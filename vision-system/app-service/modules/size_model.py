#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:57:31 2023

@author: shervin
"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

class SizeNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1= nn.Linear(2,20)
        self.fc2 = nn.Linear(20,3)
        disparities = torch.Tensor([112.5,
         91.0,
         78.5,
         69.5,
         62.0,
         57.5,
         46.5,
         41.0,
         35.5,
         32.0,
         30.0,
         27.0,
         25.0,
         24.5,
         23.0,
         22.5]).reshape(-1,1)
        self.input_scaler = MinMaxScaler().fit(disparities)
    
    def forward(self,x):
        x = self.input_scaler.transform(x)
        x = torch.Tensor(x)
        x = self.polynomial_features(x)
        
        x = self.fc1(x)
        x = nn.functional.relu(x)
        x = self.fc2(x)
        
        return x
        
    def polynomial_features(self,x):
        return torch.concat([x,x**2],dim=1)