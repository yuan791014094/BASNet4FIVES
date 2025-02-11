import os
from skimage import io, transform
import torch
import torchvision
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms#, utils
# import torch.optim as optim

import numpy as np
from PIL import Image
import glob
from os.path import join, sep
from pathlib import Path

from data_loader import RescaleT
from data_loader import CenterCrop
from data_loader import ToTensor
from data_loader import ToTensorLab
from data_loader import SalObjDataset

from model import BASNet

def normalize_prediction(d):
    """
    标准化预测值
    参数:
    d - 输入的预测值张量
    
    返回值:
    dn - 标准化后的预测值张量
    """
    # 计算输入张量d的最大值和最小值
    ma = torch.max(d)
    mi = torch.min(d)

    # 标准化处理：将输入张量d的值映射到0-1区间
    dn = (d-mi)/(ma-mi)

    return dn

def save_output(image_path, pred, d_dir):
    """
    保存预测结果的图像。

    参数:
    - image_path: 输入图像的文件名。
    - pred: 神经网络的预测结果，一个Tensor。
    - d_dir: 保存预测结果图像的目标目录。

    返回值:
    - 无
    """

    # 将预测结果从Tensor转换为numpy数组，并调整尺寸
    predict = pred
    predict = predict.squeeze()
    predict_np = predict.cpu().data.numpy()

    # 将预测结果数组转换为RGB图像
    im = Image.fromarray(predict_np * 255).convert('RGB')
    # 从输入图像名称中提取文件名
    img_name = image_path.split(sep)[-1]
    # 读取输入图像
    image = io.imread(image_path)
    # 调整预测图像的大小以匹配输入图像的大小
    imo = im.resize((image.shape[1], image.shape[0]), resample=Image.BILINEAR)

    # 将调整大小后的预测图像转换回numpy数组
    pb_np = np.array(imo)

    # 构造保存图像的文件名
    file_name_no_ext = '.'.join(img_name.split(".")[:-1])

    # 保存调整大小后的预测图像
    imo.save(join(d_dir, file_name_no_ext + '.png'))

if __name__ == '__main__':
	# --------- 1. get image path and name ---------
	
	image_dir = join('.', 'FIVES-dataset', 'test', 'Original')
	prediction_dir = join('.', 'test_results')
	model_dir = join('.', 'saved_models', 'basnet_bsi', 'basnet_bsi_5.pth')
	
	img_name_list = glob.glob(join(image_dir, '*.png'))
	
	# --------- 2. dataloader ---------
	#1. dataload
	test_salobj_dataset = SalObjDataset(
		img_name_list = img_name_list, 
        lbl_name_list = [], 
        transform=transforms.Compose([
            RescaleT(256),
            ToTensorLab(flag=0)
        ])
	)
	test_salobj_dataloader = DataLoader(
		test_salobj_dataset, 
		batch_size=1, 
		shuffle=False, 
		num_workers=1
	)
	
	# --------- 3. model define ---------
	print("...load BASNet...")
	net = BASNet(3,1)
	net.load_state_dict(torch.load(model_dir))
	if torch.cuda.is_available():
		net.cuda()
	net.eval()
	
	# --------- 4. inference for each image ---------
	for i_test, data_test in enumerate(test_salobj_dataloader):
	
		print("inferencing:", img_name_list[i_test].split(sep)[-1])
	
		inputs_test = data_test['image']
		inputs_test = inputs_test.type(torch.FloatTensor)
	
		if torch.cuda.is_available():
			inputs_test = Variable(inputs_test.cuda())
		else:
			inputs_test = Variable(inputs_test)
	
		d1, *_ = net(inputs_test)
	
		# normalization
		pred = d1[:,0,:,:]
		pred = normalize_prediction(pred)
	
		# save results to test_results folder
		save_output(img_name_list[i_test], pred, prediction_dir)
