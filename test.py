import torch
import torch.nn.functional as F


"""
x = ([0, 1] , [26, 27])
z = torch.tensor(x)
c = z.unsqueeze(0)

#ref_cls = torch.tensor([1, 4])

tensor = torch.arange(1, 17)
tensor = tensor.view(4, 4)
tensor = tensor.unsqueeze(2)
"""
"""
input_img = torch.zeros(1, 52, 64, 64)
ref_cls = torch.randint(0, 52, (input_img.size(0), 1))
trg_cls = torch.randint(0, 52, (1, 1))

def select_imgs(images_of_onefont, selected_cls):
    # given selected char classes, return selected imgs
    # images_of_onefont: [bs, 52, opts.img_size, opts.img_size]
    # selected_cls: [bs, nshot]
    nums = selected_cls.size(1) # 4
    selected_cls_ = selected_cls.unsqueeze(2)
    selected_cls_ = selected_cls_.unsqueeze(3)
    selected_cls_ = selected_cls_.expand(images_of_onefont.size(0), nums, 64, 64)         
    selected_img = torch.gather(images_of_onefont, 1, selected_cls_)
    return selected_img

#print(select_imgs(input_img, ref_cls))
tensor = torch.arange(1, 212993)

# Изменение формы тензора на 1x52x64x64
tensor = tensor.reshape(1, 52, 64, 64)
a = select_imgs(tensor, ref_cls)
b = select_imgs(tensor, trg_cls)

x = torch.arange(1, 1837)
x = x.reshape(51, 4, 9) 
def shift_right(x, pad_value=None):
    if pad_value is None:
        shifted = F.pad(x, (0, 0, 0, 0, 1, 0))[:-1, :, :]
    else:
        shifted = torch.cat([pad_value, x], axis=0)[:-1, :, :]
    return shifted
shifted_x = shift_right(x)
i = 0
print(x[i])
print(shifted_x[i])
"""


