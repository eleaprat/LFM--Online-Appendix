# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 18:13:54 2020

@author: emapr
"""
import pandas as pd
from Case import system_input

def PTDF_check(D,G,Quantity,offer_bus,request_bus,direction):
    
    epsilon=0.00001

    data  = system_input(D,G)
    nodes = data['nodes']                 # index for nodes
    lines = data['lines']                 # index for lines
    
    PTDF = pd.read_csv('PTDF.csv', names = nodes)
    PTDF['Line'] = lines
    PTDF.set_index('Line', inplace = True)
    
    lines_cstr = data['lines_cstr']       # index for constrained lines

    # Initial state
    Pl_max_pos = []
    Pl_max_neg = []
    Pl_flow=[]
    for l in lines_cstr:
        Pl = 0
        for i in nodes:
            Pl += PTDF.loc[l,i] * (data[i]['generation']-data[i]['demand'])
        if abs(Pl) > (data[l]['lineCapacity']+epsilon):
            print('The initial dispatch is not feasible ({})'.format(l))
        Pl_max_pos.append(data[l]['lineCapacity']-Pl)
        Pl_max_neg.append(-data[l]['lineCapacity']-Pl)
        Pl_flow.append(Pl)

    if direction == 'Up':
        k = nodes[offer_bus]
        m = nodes[request_bus]
    if direction == 'Down':
        m = nodes[offer_bus]
        k = nodes[request_bus]
    
    # print('------')
    
    for l in lines_cstr:
        x = lines_cstr.index(l)

        PTDF_diff = - (PTDF.loc[l,m] - PTDF.loc[l,k])
        if PTDF_diff > epsilon:
            Pl_max = max(Pl_max_pos[x],0)
        elif PTDF_diff < -epsilon:
            Pl_max = min(Pl_max_neg[x],0)
        if PTDF_diff > epsilon or PTDF_diff < -epsilon:
            if Pl_max/PTDF_diff < Quantity:
                Quantity = Pl_max/PTDF_diff
        #     print('{} - Pl: {}, Capacity: {}, Pl_max_pos: {}, Pl_max_neg: {}, PTDF_diff: {}, Pl_max/PTDF_diff: {}'.format(l, round(Pl_flow[x],2), round(data[l]['lineCapacity'],2), round(Pl_max_pos[x],2), round(Pl_max_neg[x],2),round(PTDF_diff,2),round(Pl_max/PTDF_diff,2)))
        # else:
        #     print('{} - Pl: {}, Capacity: {}, Pl_max_pos: {}, Pl_max_neg: {}, PTDF_diff: {}'.format(l, round(Pl_flow[x],2), round(data[l]['lineCapacity'],2), round(Pl_max_pos[x],2), round(Pl_max_neg[x],2),round(PTDF_diff,2)))
    return Quantity

# D = [0,0.04,0.07,0.14,0.04,0.14,0.14,0.07,0.07,0.04,0.14,0.07,0.04,0.07,0.14]
# G = [1.21, 0.03, 0.060000000000000546, -0.010000000000000342, 0.0, -0.03, -0.03, 0.06, -0.09000000000000055, 0.06000000000000176, 0, -0.05000000000000142, 0, 0, 0]
# Quantity = 0.06
# offer_bus = 9
# request_bus = 2
# direction = 'Up'
# Quantity = PTDF_check(D,G,Quantity,offer_bus,request_bus,direction)
