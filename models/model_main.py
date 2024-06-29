from .image_encoder import ImageEncoder
from .image_decoder import ImageDecoder
from .modality_fusion import ModalityFusion
from .vgg_perceptual_loss import VGGPerceptualLoss
from .transformers import *
from torch.autograd import Variable

class ModelMain(nn.Module):

    def __init__(self, opts, mode='train'):
        super().__init__()
        self.opts = opts
        self.img_encoder = ImageEncoder(img_size=opts.img_size, input_nc=opts.ref_nshot, ngf=opts.ngf, norm_layer=nn.LayerNorm)
        self.img_decoder = ImageDecoder(img_size=opts.img_size, input_nc=opts.bottleneck_bits + opts.char_num, output_nc=1, ngf=opts.ngf, norm_layer=nn.LayerNorm)
        self.vggptlossfunc = VGGPerceptualLoss()
        self.modality_fusion = ModalityFusion(img_size=opts.img_size, ref_nshot=opts.ref_nshot, bottleneck_bits=opts.bottleneck_bits, ngf=opts.ngf, mode=opts.mode)
        self.transformer_main = Transformer(
            input_channels = 1,        
            input_axis = 2,              # number of axis for input data (2 for images, 3 for video)
            num_freq_bands = 6,          # number of freq bands, with original value (2 * K + 1)
            max_freq = 10.,              # maximum frequency, hyperparameter depending on how fine the data is
            depth = 6,                   # depth of net. The shape of the final attention mechanism will be:
                                         # depth * (cross attention -> self_per_cross_attn * self attention)
            num_latents = 256,           # number of latents, or induced set points, or centroids. different papers giving it different names
            latent_dim = opts.dim_seq_latent,            # latent dimension
            cross_heads = 1,             # number of heads for cross attention. paper said 1
            latent_heads = 8,            # number of heads for latent self attention, 8
            cross_dim_head = 64,         # number of dimensions per cross attention head
            latent_dim_head = 64,        # number of dimensions per latent self attention head
            num_classes = 1000,          # output number of classes
            attn_dropout = 0.,
            ff_dropout = 0.,
            weight_tie_layers = False,   # whether to weight tie layers (optional, as indicated in the diagram)
            fourier_encode_data = True,  # whether to auto-fourier encode the data, using the input_axis given. defaults to True, but can be turned off if you are fourier encoding the data yourself
            self_per_cross_attn = 2      # number of self attention blocks per cross attention
            )

        self.transformer_seqdec = Transformer_decoder()


    def forward(self, data, mode='train'):

        """
        imgs = ref_img, trg_img
        seqs = ref_seq, ref_seq_cat, ref_pad_mask, trg_seq, trg_seq_gt, trg_seq_shifted, trg_pts_aux
        scalars = trg_char_onehot, trg_cls, trg_seqlen

        Подается trg, ref imgs, trg, ref seqs, trg_shift seq, trg_gt seq, trg pts aux, onehot trg char,
        trg cls, trg seq len
        """
        
        imgs, seqs, scalars = self.fetch_data(data, mode)
        ref_img, trg_img = imgs
        ref_seq, ref_seq_cat, ref_pad_mask, trg_seq, trg_seq_gt, trg_seq_shifted, trg_pts_aux = seqs
        trg_char_onehot, trg_cls, trg_seqlen = scalars

        # image encoding
        img_encoder_out = self.img_encoder(ref_img)
        img_feat = img_encoder_out['img_feat'] # bs, ngf * (2 ** 6) 
        """
        Получили одномернвй тензор перед подачей в полносвязные слои
        """

        # seq encoding
        ref_img_ = ref_img.view(ref_img.size(0) * ref_img.size(1), ref_img.size(2), ref_img.size(3)).unsqueeze(-1) # [max_seq_len, bs * n_ref, 9]
        seq_feat, _ = self.transformer_main(ref_img_, ref_seq_cat, mask=ref_pad_mask) # [n_bs * n_ref, max_seq_len + 1, 9]

        # modality funsion
        mf_output, latent_feat_seq = self.modality_fusion(seq_feat, img_feat, ref_pad_mask=ref_pad_mask) 
        latent_feat_seq = self.transformer_main.att_residual(latent_feat_seq) # [n_bs, max_seq_len + 1, bottleneck_bits]
        z = mf_output['latent']
        kl_loss = mf_output['kl_loss']

        # image decoding
        img_decoder_out = self.img_decoder(z, trg_char_onehot, trg_img)

        ret_dict = {}
        loss_dict = {}

        ret_dict['img'] = {}
        ret_dict['img']['out'] = img_decoder_out['gen_imgs']
        ret_dict['img']['ref'] = ref_img
        ret_dict['img']['trg'] = trg_img
        
        if mode in {'train', 'val'}:
            # seq decoding (training or val mode)
            tgt_mask = Variable(subsequent_mask(self.opts.max_seq_len).type_as(ref_pad_mask.data)).unsqueeze(0).expand(z.size(0), -1, -1, -1).cuda().float()
            command_logits, args_logits, attn = self.transformer_seqdec(x=trg_seq_shifted, memory=latent_feat_seq, trg_char=trg_cls, tgt_mask=tgt_mask)
            command_logits_2, args_logits_2 = self.transformer_seqdec.parallel_decoder(command_logits, args_logits, memory=latent_feat_seq.detach(), trg_char=trg_cls)

            total_loss = self.transformer_main.loss(command_logits, args_logits,trg_seq, trg_seqlen, trg_pts_aux)
            total_loss_parallel = self.transformer_main.loss(command_logits_2, args_logits_2, trg_seq, trg_seqlen, trg_pts_aux)
            vggpt_loss = self.vggptlossfunc(img_decoder_out['gen_imgs'], trg_img)
            # loss and output
            loss_svg_items = ['total', 'cmd', 'args', 'smt', 'aux']
            # for image
            loss_dict['img'] = {}
            loss_dict['img']['l1'] = img_decoder_out['img_l1loss']
            loss_dict['img']['vggpt'] = vggpt_loss['pt_c_loss']
            # for latent
            loss_dict['kl'] = kl_loss
            # for svg
            loss_dict['svg'] = {}
            loss_dict['svg_para'] = {}
            for item in loss_svg_items:
                loss_dict['svg'][item] = total_loss[f'loss_{item}']
                loss_dict['svg_para'][item] = total_loss_parallel[f'loss_{item}']
            
        else: # testing (inference)

            trg_len = trg_seq_shifted.size(0)
            sampled_svg = torch.zeros(1, trg_seq.size(1), self.opts.dim_seq_short).cuda()

            for t in range(0, trg_len):
                tgt_mask = Variable(subsequent_mask(sampled_svg.size(0)).type_as(ref_seq_cat.data)).unsqueeze(0).expand(sampled_svg.size(1), -1, -1, -1).cuda().float()
                command_logits, args_logits, attn = self.transformer_seqdec(x=sampled_svg, memory=latent_feat_seq, trg_char=trg_cls, tgt_mask=tgt_mask)
                prob_comand = F.softmax(command_logits[:, -1, :], -1)
                prob_args = F.softmax(args_logits[:, -1, :], -1)
                next_command = torch.argmax(prob_comand, -1).unsqueeze(-1)
                next_args = torch.argmax(prob_args, -1)
                predict_tmp = torch.cat((next_command, next_args),-1).unsqueeze(1).transpose(0,1)
                sampled_svg = torch.cat((sampled_svg, predict_tmp), dim=0)

            sampled_svg =  sampled_svg[1:]
            cmd2 = sampled_svg[:,:,0].unsqueeze(-1)
            arg2 = sampled_svg[:,:,1:]
            
            
            command_logits_2, args_logits_2 = self.transformer_seqdec.parallel_decoder(cmd_logits=cmd2, args_logits=arg2, memory=latent_feat_seq, trg_char=trg_cls)
            prob_comand = F.softmax(command_logits_2,-1)
            prob_args = F.softmax(args_logits_2,-1)
            update_command = torch.argmax(prob_comand,-1).unsqueeze(-1)
            update_args = torch.argmax(prob_args,-1)
            sampled_svg_parralel = torch.cat((update_command, update_args),-1).transpose(0,1)

            commands1 = F.one_hot(sampled_svg[:,:,:1].long(), 4).squeeze().transpose(0, 1)
            args1 = denumericalize(sampled_svg[:,:,1:]).transpose(0,1)
            sampled_svg_1 = torch.cat([commands1.cpu().detach(),args1[:, :, 2:].cpu().detach()],dim =-1)
            
            
            commands2 = F.one_hot(sampled_svg_parralel[:, :, :1].long(), 4).squeeze().transpose(0, 1)
            args2 = denumericalize(sampled_svg_parralel[:, :, 1:]).transpose(0,1)
            sampled_svg_2 = torch.cat([commands2.cpu().detach(),args2[:, :, 2:].cpu().detach()], dim =-1)

            ret_dict['svg'] = {}
            ret_dict['svg']['sampled_1'] = sampled_svg_1
            ret_dict['svg']['sampled_2'] = sampled_svg_2
            ret_dict['svg']['trg'] = trg_seq_gt

        return ret_dict, loss_dict

    def fetch_data(self, data, mode):
        """
        - sequance [1, 52, 51, 12] - 4 бин показатель команды + 8 точек (начальаная, 1-вспомогательная, 2-вспомогательная, конечная)
        - sequance_relax 52 x 612: 
            mod 6 == 1: бинарный показатель EOS
            mod 6 == 2: бинарный показатель MOVE
            mod 6 == 3: бинарный показатель LINE 
            mod 6 == 4: бинарный показатель BIES
            mod 6 == 5/0: x/y 
        - class: 52 x 1 c нулями
        - font_id - название шрифта
        - pts_aux - 52 x 51 x 6 - координаты точек (?)
        - rendered_64 - 52 x 64 x 64 c значениями 255
        - seq_len - 52x1 
        """
        input_image = data['rendered'] # [bs, opts.char_num, opts.img_size, opts.img_size] Тензор  bsх52х64х64 каждый слой - 1 буква в png.
        input_sequence = data['sequence'] # [bs, opts.char_num, opts.max_seq_len] bsх52х51
        input_seqlen = data['seq_len'] 
        input_seqlen = input_seqlen + 1
        input_pts_aux = data['pts_aux']
        arg_quant = numericalize(input_sequence[:, :, :, 4:]) # отрезаются команды, остаются 8 точек и нормализуются в значения от 0 до 127
        cmd_cls = torch.argmax(input_sequence[:, :, :, :4], dim=-1).unsqueeze(-1) # переделывает тензор из бинарных команд в тензор [1, 52, 51, 1] где записаны номер команды (0 до 3) если нет команды - 0, если команда EOS - 0
        input_sequence = torch.cat([cmd_cls, arg_quant], dim=-1) # конкат двух предыдущих тензеров = [1, 52, 51, 9], 9 = 1 - команда + 8 точки

        input_image_italic = data['rendered'] # [bs, opts.char_num, opts.img_size, opts.img_size] Тензор  bsх52х64х64 каждый слой - 1 буква в png. 
        input_sequence_italic = data['sequence'] # [bs, opts.char_num, opts.max_seq_len] bsх52х51
        input_seqlen_italic = data['seq_len'] 
        input_seqlen_italic = input_seqlen + 1
        input_pts_aux_italic = data['pts_aux']
        arg_quant_italic = numericalize(input_sequence_italic[:, :, :, 4:]) # отрезаются команды, остаются 8 точек и нормализуются в значения от 0 до 127
        cmd_cls_italic = torch.argmax(input_sequence_italic[:, :, :, :4], dim=-1).unsqueeze(-1) # переделывает тензор из бинарных команд в тензор [1, 52, 51, 1] где записаны номер команды (0 до 3) если нет команды - 0, если команда EOS - 0
        input_sequence_italic = torch.cat([cmd_cls_italic, arg_quant_italic], dim=-1) # конкат двух предыдущих тензеров = [1, 52, 51, 9], 9 = 1 - команда + 8 точки
        # choose reference classes and target classes
        if mode == 'train':
            ref_cls = torch.randint(0, self.opts.char_num, (input_image.size(0), self.opts.ref_nshot)).cuda()  # input_image.size(0) - bs, тензор [bs, ref_nshot] с rnd значениям от 0 до 51, для каждого bs
        elif mode == 'val':
            ref_cls = torch.arange(0, self.opts.ref_nshot, 1).unsqueeze(0).expand(input_image.size(0), -1) # создается тензор [ref_nshot, bs] c в каждой строке 0 до ref_nshot
        else:
            ref_ids = self.opts.ref_char_ids.split(',')
            ref_ids = list(map(int, ref_ids))
            assert len(ref_ids) == self.opts.ref_nshot
            ref_cls = torch.tensor(ref_ids).cuda().unsqueeze(0).expand(self.opts.char_num, -1)
        
        if mode in {'train', 'val'}:
            trg_cls = torch.randint(0, self.opts.char_num, (input_image_italic.size(0), 1)).cuda() # input_image.size(0) - bs, тензор 1хbs с rnd значениям от 0 до 51, для каждого bs
        else:
            trg_cls = torch.arange(0, self.opts.char_num).cuda() 
            trg_cls = trg_cls.view(self.opts.char_num, 1)
            """
            Меняем первую размерность с bs на char_num (52)
            """
            input_image = input_image.expand(self.opts.char_num, -1, -1, -1)
            input_sequence = input_sequence.expand(self.opts.char_num, -1, -1, -1)
            input_pts_aux = input_pts_aux.expand(self.opts.char_num, -1, -1, -1)
            input_seqlen = input_seqlen.expand(self.opts.char_num, -1, -1)

        ref_img = util_funcs.select_imgs(input_image, ref_cls, self.opts) # [bs/char_num, nshots, 64, 64]  выбирает из тензора всех букв слой 4 букв 
        # select a target glyph image
        trg_img = util_funcs.select_imgs(input_image_italic, trg_cls, self.opts) # [bs/char_num, nshots, 64, 64] выбирает из тензора всех букв слой 1 буквы 
        # randomly select ref vector glyphs
        ref_seq = util_funcs.select_seqs(input_sequence, ref_cls, self.opts, self.opts.dim_seq_short) # [batch_size, ref_nshot, max_seq_len, dim_seq_nmr] получаем тезор последовательной для 4 букв но я не знаю той же что и ref_img или нет? и последовательной каких конкретно?
        # randomly select a target vector glyph
        trg_seq = util_funcs.select_seqs(input_sequence_italic, trg_cls, self.opts, self.opts.dim_seq_short) # [batch_size, 1, max_seq_len (51), dim_seq_nmr (9)] получаем тезор последовательной для 1 буквы но я не знаю той же что и trg_img или нет?
        trg_seq = trg_seq.squeeze(1) # [bs, max_seq_len (51), dim_seq_nmr (9)] отвечающую за кол-во букв 
        
        trg_pts_aux = util_funcs.select_seqs(input_pts_aux_italic, trg_cls, self.opts, opts.n_aux_pts) # [bs, 1, max_seq_len (51), count_pts_aux (9)] тезор вспомогательных точек для trg буквы
        trg_pts_aux = trg_pts_aux.squeeze(1)

        # the one-hot target char class
        trg_char_onehot = util_funcs.trgcls_to_onehot(trg_cls, self.opts) # one-hot кодировка trg_cls
        
        # shift target sequence
        trg_seq_gt = trg_seq.clone().detach() # копируем trg_seq но не вычисляем градиент  
        trg_seq_gt = torch.cat((trg_seq_gt[:, :, :1], trg_seq_gt[:, :, 3:]), -1) # [bs, max_len_seq, 7] режит конечную у прошлой и начальную у текущей
        trg_seq = trg_seq.transpose(0, 1)
        trg_seq_shifted = util_funcs.shift_right(trg_seq) # сдвигаем все команды на позицию право, 1 команда - 0, вторая команда та, которая у trg_seq была 1 

        ref_seq_cat = ref_seq.view(ref_seq.size(0) * ref_seq.size(1), ref_seq.size(2), ref_seq.size(3)) # [bs * nshot, max_seq_len, 9]
        ref_seq_cat = ref_seq_cat.transpose(0,1) # [max_seq_len, bs * nshot, 9]
        
        ref_seqlen = util_funcs.select_seqlens(input_seqlen, ref_cls, self.opts) # тензор с длинными последовательностей для ref
        ref_seqlen_cat = ref_seqlen.view(ref_seqlen.size(0) * ref_seqlen.size(1), ref_seqlen.size(2))

        ref_pad_mask = torch.zeros(ref_seqlen_cat.size(0), self.opts.max_seq_len) # value = 1 means pos to be masked
        for i in range(ref_seqlen_cat.size(0)):
            ref_pad_mask[i,:ref_seqlen_cat[i]] = 1
        ref_pad_mask = ref_pad_mask.cuda().float().unsqueeze(1)

        trg_seqlen = util_funcs.select_seqlens(input_seqlen_italic, trg_cls, self.opts) # тензор с длинными последовательностей для trg
        trg_seqlen = trg_seqlen.squeeze()

        return [ref_img, trg_img], [ref_seq, ref_seq_cat, ref_pad_mask, trg_seq, trg_seq_gt, trg_seq_shifted, trg_pts_aux], [trg_char_onehot, trg_cls, trg_seqlen]