import torch
import torch.nn.functional as F

"""
args_logits : torch.Size([bs, 51, 8, 128])
trg_seq : torch.Size([51, bs, 9])
trg_seqlen : torch.Size([bs]) 
trg_pts_aux : torch.Size([bs, 51, 6]
"""
def sequence_mask(lengths, max_len=None):
    batch_size=lengths.numel()
    max_len=max_len or lengths.max()
    return (torch.arange(0, max_len, device=lengths.device)
    .type_as(lengths)
    .unsqueeze(0).expand(batch_size,max_len)
    .lt(lengths.unsqueeze(1)))

def denumericalize(cmd, n=128):
    cmd = cmd / n * 30 
    return cmd

def loss(self, cmd_logits, args_logits, trg_seq, trg_seqlen, trg_pts_aux):
        '''
        Inputs:
        cmd_logits: [b, 51, 4]
        args_logits: [b, 51, 6]
        '''
        
        cmd_args_mask =  torch.Tensor([[0, 0, 0., 0., 0., 0., 0., 0.],
                                       [1, 1, 0., 0., 0., 0., 1., 1.],
                                       [1, 1, 0., 0., 0., 0., 1., 1.],
                                       [1, 1, 1., 1., 1., 1., 1., 1.]]).to(cmd_logits.device)  
        
        tgt_commands = trg_seq[:,:,:1].transpose(0,1)
        tgt_args = trg_seq[:,:,1:].transpose(0,1)
        
        seqlen_mask = sequence_mask(trg_seqlen, max_seq_len).unsqueeze(-1)
        seqlen_mask2 = seqlen_mask.repeat(1,1,4)# NOTE b,501,4
        seqlen_mask4 = seqlen_mask.repeat(1,1,8)
        seqlen_mask3 = seqlen_mask.unsqueeze(-1).repeat(1,1,8,128)
        
        
        tgt_commands_onehot = F.one_hot(tgt_commands, 4)
        tgt_args_onehot = F.one_hot(tgt_args, 128)
       
        args_mask = torch.matmul(tgt_commands_onehot.float(),cmd_args_mask).squeeze()


        loss_cmd = torch.sum(- tgt_commands_onehot.squeeze() * F.log_softmax(cmd_logits, -1), -1)
        loss_cmd = torch.mul(loss_cmd, seqlen_mask.squeeze())
        loss_cmd = torch.mean(torch.sum(loss_cmd/trg_seqlen.unsqueeze(-1),-1))
        
        loss_args = (torch.sum(-tgt_args_onehot*F.log_softmax(args_logits,-1),-1)*seqlen_mask4*args_mask)
     
        loss_args = torch.mean(loss_args,dim=-1,keepdim=False)
        loss_args = torch.mean(torch.sum(loss_args/trg_seqlen.unsqueeze(-1),-1))

        SE_mask =  torch.Tensor([[1, 1],
                                 [0, 0],
                                 [1, 1],
                                 [1, 1]]).to(cmd_logits.device)  
        
        SE_args_mask = torch.matmul(tgt_commands_onehot.float(),SE_mask).squeeze().unsqueeze(-1)
        
        
        args_prob = F.softmax(args_logits, -1)
        args_end = args_prob[:,:,6:]
        args_end_shifted = torch.cat((torch.zeros(args_end.size(0),1,args_end.size(2),args_end.size(3)).to(args_end.device),args_end),1)
        args_end_shifted = args_end_shifted[:,: max_seq_len,:,:]
        args_end_shifted = args_end_shifted*SE_args_mask + args_end*(1-SE_args_mask)
        
        args_start = args_prob[:,:,:2]

        seqlen_mask5 = sequence_mask(trg_seqlen-1, max_seq_len).unsqueeze(-1)
        seqlen_mask5 = seqlen_mask5.repeat(1,1,2)
       
        smooth_constrained = torch.sum(torch.pow((args_end_shifted - args_start), 2), -1) * seqlen_mask5
        smooth_constrained = torch.mean(smooth_constrained, dim=-1, keepdim=False)
        smooth_constrained = torch.mean(torch.sum(smooth_constrained / (trg_seqlen - 1).unsqueeze(-1), -1))

        args_prob2 = F.softmax(args_logits / 0.1, -1)

        c = torch.argmax(args_prob2,-1).unsqueeze(-1).float() - args_prob2.detach()
        p_argmax = args_prob2 + c
        p_argmax = torch.mean(p_argmax,-1)       
        control_pts = denumericalize(p_argmax)
        
        p0 = control_pts[:,:,:2]
        p1 = control_pts[:,:,2:4]
        p2 = control_pts[:,:,4:6]
        p3 = control_pts[:,:,6:8]
        
        line_mask = (tgt_commands==2).float() + (tgt_commands==1).float() 
        curve_mask = (tgt_commands==3).float() 
        
        t=0.25
        aux_pts_line = p0 + t*(p3-p0)
        for t in [0.5,0.75]:
            coord_t = p0 + t*(p3-p0)
            aux_pts_line = torch.cat((aux_pts_line,coord_t),-1)
        aux_pts_line = aux_pts_line*line_mask
        
        t=0.25
        aux_pts_curve = (1-t)*(1-t)*(1-t)*p0 + 3*t*(1-t)*(1-t)*p1 + 3*t*t*(1-t)*p2 + t*t*t*p3
        for t in [0.5, 0.75]:
            coord_t = (1-t)*(1-t)*(1-t)*p0 + 3*t*(1-t)*(1-t)*p1 + 3*t*t*(1-t)*p2 + t*t*t*p3
            aux_pts_curve = torch.cat((aux_pts_curve,coord_t),-1)
        aux_pts_curve = aux_pts_curve * curve_mask
        
        
        aux_pts_predict = aux_pts_curve + aux_pts_line
        seqlen_mask_aux = sequence_mask(trg_seqlen - 1, max_seq_len).unsqueeze(-1)
        aux_pts_loss = torch.pow((aux_pts_predict - trg_pts_aux), 2) * seqlen_mask_aux
        
        loss_aux = torch.mean(aux_pts_loss, dim=-1, keepdim=False)
        loss_aux = torch.mean(torch.sum(loss_aux / trg_seqlen.unsqueeze(-1), -1))

        
        loss = loss_w_cmd * loss_cmd + loss_w_args * loss_args + loss_w_aux * loss_aux + loss_w_smt * smooth_constrained 

        svg_losses = {}
        svg_losses['loss_total'] = loss
        svg_losses["loss_cmd"] = loss_cmd
        svg_losses["loss_args"] = loss_args
        svg_losses["loss_smt"] = smooth_constrained
        svg_losses["loss_aux"] = loss_aux

        return svg_losses