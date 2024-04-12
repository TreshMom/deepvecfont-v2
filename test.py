import torch
x = ([0, 1] , [26, 27])
z = torch.tensor(x)
c = z.unsqueeze(0)
print(z)