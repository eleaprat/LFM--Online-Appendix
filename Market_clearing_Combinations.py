# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 13:31:09 2020

@author: emapr
"""

from Case import system_input
import pandas as pd
from PTDF_check import PTDF_check
from itertools import combinations
from operator import add
import time

# Function to match an offer
def matching(bid_type, G, D, Social_Welfare, offer_index, offer_direction, offer_bus, offer_quantity, offer_price, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal):
    
    epsilon = 0.00001 # Tolerance
    status = 'no match'
    PTDF_calc = 0
    comb=[]
    
# The bid is of type Offer-Up
    if offer_direction == 'Up':
        if Requests_Up.empty:
            print('All requests up have already been matched.')
        for RU in Requests_Up.index:
            if offer_price <= Requests_Up.at[RU,'Price']:
                Offered = offer_quantity
                Requested = Requests_Up.at[RU,'Quantity']
                Quantity = min(Offered,Requested)
                request_bus = nodes.index(Requests_Up.at[RU,'Bus'])
                
                # Check for this request only
                Quantity = PTDF_check(D,G,Quantity,offer_bus,request_bus,offer_direction)
                PTDF_calc+=1
                
                # Check all combinations if this request alone is feasible
                if Quantity > epsilon and not Accepted_Requests_Conditionnal.empty:
                    # Create all combinations
                    cond_requests = list(Accepted_Requests_Conditionnal.index)
                    comb=[]
                    for i in range(len(cond_requests)):
                        new_comb = [list(l) for l in combinations(cond_requests,i+1)]
                        for n in new_comb:
                            comb.append(n)
                    # Remove combinations for up and down regulation at the same bus
                    for ra in range(len(Accepted_Requests_Conditionnal.index)-1):
                        first = Accepted_Requests_Conditionnal.index[ra]
                        second = Accepted_Requests_Conditionnal.index[ra+1]
                        if Accepted_Requests_Conditionnal.at[first,'Bus'] == Accepted_Requests_Conditionnal.at[second,'Bus'] and Accepted_Requests_Conditionnal.at[first,'Direction'] != Accepted_Requests_Conditionnal.at[second,'Direction']:
                            for c in comb:
                                if first in c and second in c:
                                    comb.remove(c)
                    print('Number of combinations: {}'.format(len(comb)))
                    # PTDF check for all combinations
                    for c in comb:
                        if Quantity > epsilon:
                            G_new = G
                            for i in c:
                                G_new = list(map(add,Accepted_Requests_Conditionnal.at[i,'Dispatch Change'],G_new))
                            Quantity = PTDF_check(D,G_new,Quantity,offer_bus,request_bus,offer_direction)
                            PTDF_calc+=1
                        else:
                            break
                
                if Quantity > epsilon: # Line constraints are respected
                    print('Offer {} (up, bus {}) matched with Request {} (up, bus {}) for a quantity of {} MW'.format(offer_index,nodes[offer_bus],RU,Requests_Up['Bus'][RU],round(Quantity,3)))
                    Delta_G = [0] * len(G)
                    Delta_G[offer_bus]+=Quantity
                    Delta_G[request_bus]-=Quantity
                    if Requests_Up.at[RU,'Type'] == 'Unconditionnal':
                        G = list(map(add,G,Delta_G))
                        status = 'match'
                    elif Requests_Up.at[RU,'Type'] == 'Conditionnal':
                        # Check if request is already in accepted requests
                        if RU in Accepted_Requests_Conditionnal.index:
                            # If so, update the dispatch change to inlcude the new offer
                            Delta_G_init = Accepted_Requests_Conditionnal.at[RU,'Dispatch Change']
                            Delta_G_init = list(map(add,Delta_G_init,Delta_G))
                            Accepted_Requests_Conditionnal.at[RU,'Dispatch Change'] = Delta_G_init
                        # If not, create it
                        else:
                            Accepted_Requests_Conditionnal.loc[RU]=[Requests_Up.at[RU,'Bus'],'Up',Delta_G]
                            Accepted_Requests_Conditionnal.sort_values(by=['Bus'], inplace=True) # Reorganize to group requests per node
                    Social_Welfare += Quantity * (Requests_Up.at[RU,'Price']-offer_price)
                    offer_quantity = Offered - Quantity
                    Requests_Up.at[RU,'Quantity'] = Requested - Quantity
                    if Requests_Up.at[RU,'Quantity'] < epsilon: # If the request was completely matched
                        Requests_Up = Requests_Up.drop([RU], axis=0)
                    if offer_quantity < epsilon: # If the offer was completely matched
                        if bid_type == 'new':
                            print('{} PTDF verifications have been performed'.format(PTDF_calc))
                            return G, D, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal
                        elif bid_type == 'old':
                            Offers = Offers.drop([offer_index], axis=0)
                else:
                    print('Offer {} (up, bus {}) cannot match with Request {} (up, bus {}) due to line congestions.'.format(offer_index,nodes[offer_bus],RU,Requests_Up['Bus'][RU]))
            else:
                print('{} PTDF verifications have been performed'.format(PTDF_calc))
                print('There are no Requests matching Offer {} (up, bus {}) in terms of price.'.format(offer_index,nodes[offer_bus]))
                break
        if offer_quantity > epsilon: # If the offer was not completely matched, update and order the book
            Offers.loc[offer_index]=[nodes[offer_bus],offer_direction,offer_quantity,offer_price]
            Offers.sort_values(by=['Price'], ascending=True, inplace=True)
        
# The bid is of type Offer-Down
    elif offer_direction == 'Down':
        if Requests_Down.empty:
            print('All requests down have already been matched.')
        for RD in Requests_Down.index:
            if offer_price <= Requests_Down.at[RD,'Price']:
                Offered = offer_quantity
                Requested = Requests_Down.at[RD,'Quantity']
                Quantity = min(Offered,Requested)
                request_bus = nodes.index(Requests_Down.at[RD,'Bus'])
                
                # Check for this request only
                Quantity = PTDF_check(D,G,Quantity,offer_bus,request_bus,offer_direction)
                PTDF_calc+=1
                
                # Check all combinations if this request alone is feasible
                if Quantity > epsilon and not Accepted_Requests_Conditionnal.empty:
                    # Create all combinations
                    cond_requests = Accepted_Requests_Conditionnal.index
                    comb=[]
                    for i in range(len(cond_requests)):
                        new_comb = [list(l) for l in combinations(cond_requests,i+1)]
                        for n in new_comb:
                            comb.append(n)
                    # Remove combinations for up and down regulation at the same bus
                    for ra in range(len(Accepted_Requests_Conditionnal.index)-1):
                        first = Accepted_Requests_Conditionnal.index[ra]
                        second = Accepted_Requests_Conditionnal.index[ra+1]
                        if Accepted_Requests_Conditionnal.at[first,'Bus'] == Accepted_Requests_Conditionnal.at[second,'Bus'] and Accepted_Requests_Conditionnal.at[first,'Direction'] != Accepted_Requests_Conditionnal.at[second,'Direction']:
                            for c in comb:
                                if first in c and second in c:
                                    comb.remove(c)
                    print('Number of combinations: {}'.format(len(comb)))
                    # PTDF check for all combinations
                    for c in comb:
                        if Quantity > epsilon:
                            G_new = G
                            for i in c:
                                G_new = list(map(add,Accepted_Requests_Conditionnal.at[i,'Dispatch Change'],G_new))
                            Quantity = PTDF_check(D,G_new,Quantity,offer_bus,request_bus,offer_direction)
                            PTDF_calc+=1
                        else:
                            break
                        
                if Quantity > epsilon: # Line constraints are respected
                    print('Offer {} (down, bus {}) matched with Request {} (down, bus {}) for a quantity of {} MW'.format(offer_index,nodes[offer_bus],RD,Requests_Down['Bus'][RD],round(Quantity,3)))
                    Delta_G = [0] * len(G)
                    Delta_G[offer_bus]-=Quantity
                    Delta_G[request_bus]+=Quantity
                    if Requests_Down.at[RD,'Type'] == 'Unconditionnal':
                        G = list(map(add,G,Delta_G))
                        status = 'match'
                    elif Requests_Down.at[RD,'Type'] == 'Conditionnal':
                        # Check if request is already in accepted requests
                        if RD in Accepted_Requests_Conditionnal.index:
                            # If so, update the dispatch change to inlcude the new offer
                            Delta_G_init = Accepted_Requests_Conditionnal.at[RD,'Dispatch Change']
                            Delta_G_init = list(map(add,Delta_G_init,Delta_G))
                            Accepted_Requests_Conditionnal.at[RD,'Dispatch Change'] = Delta_G_init
                        # If not, create it
                        else:
                            Accepted_Requests_Conditionnal.loc[RD]=[Requests_Down.at[RD,'Bus'],'Down',Delta_G]
                            Accepted_Requests_Conditionnal.sort_values(by=['Bus'], inplace=True) # Reorganize to group requests per node
                        
                    Social_Welfare += Quantity * (Requests_Down.at[RD,'Price']-offer_price)
                    offer_quantity = Offered - Quantity
                    Requests_Down.at[RD,'Quantity'] = Requested - Quantity
                    if Requests_Down.at[RD,'Quantity'] < epsilon: # If the request was completely matched
                        Requests_Down = Requests_Down.drop([RD], axis=0)
                    if offer_quantity < epsilon: # If the offer was completely matched
                        if bid_type == 'new':
                            print('{} PTDF verifications have been performed'.format(PTDF_calc))
                            return G, D, status,  Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal
                        elif bid_type == 'old':
                            Offers = Offers.drop([offer_index], axis=0)
                else:
                    print('Offer {} (down, bus {}) cannot match with Request {} (down, bus {}) due to line congestions.'.format(offer_index,nodes[offer_bus],RD,Requests_Down['Bus'][RD]))
            else:
                print('{} PTDF verifications have been performed'.format(PTDF_calc))
                print('There are no Requests matching Offer {} (down, bus {}) in terms of price.'.format(offer_index,nodes[offer_bus]))
                break
        if offer_quantity > epsilon: # If the request was not completely matched, update and order the book
            Offers.loc[offer_index]=[nodes[offer_bus],offer_direction,offer_quantity,offer_price]
            Offers.sort_values(by=['Price'], ascending=True, inplace=True)
    
    print('{} PTDF verifications have been performed'.format(PTDF_calc))
    
    return G, D, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal

# Case data
D = [0,0.04,0.07,0.14,0.04,0.14,0.14,0.07,0.07,0.04,0.14,0.07,0.04,0.07,0.14]
G = [1.21,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

data  = system_input(D,G)

baseMVA = data['baseMVA']             # Base for pu calculation
nodes = data['nodes']                 # index for nodes

Requests = pd.read_csv('requests_V5.csv')
Requests_Up = Requests[(Requests.Direction == 'Up')]
Requests_Down = Requests[(Requests.Direction == 'Down')]
all_bids = pd.read_csv('offers_V4.csv')

# Dataframe with the bids
Offers = pd.DataFrame(columns = ['Bus','Direction','Quantity','Price'])
# Dataframe with the accepted conditionnal requests
Accepted_Requests_Conditionnal = pd.DataFrame(columns = ['Bus','Direction','Dispatch Change'])

Social_Welfare = 0


# Check the power flows using PTDFs each time an offer is added
for b in all_bids.index:
    
    print('------ Betting round nb {} ------ '.format(b+1))
    
    new_bid = all_bids.loc[b].copy()
    print('New bid: ({}, {}, {}, {})'.format(new_bid.at['Bus'],new_bid.at['Direction'],round(new_bid.at['Quantity'],3),new_bid.at['Price']))
    
    offer_bus = nodes.index(new_bid.at['Bus'])
    offer_direction = new_bid.at['Direction']
    offer_price = new_bid.at['Price']
    offer_quantity = new_bid.at['Quantity']
    
    start_time = time.time()
    G, D, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal = matching('new',G, D, Social_Welfare, b, offer_direction, offer_bus, offer_quantity, offer_price, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal)
    duration=time.time()-start_time
    print('Computation time: {}s'.format(round(duration,3)))
    # print('Offers:')
    # print(Offers)
    
    if Requests_Up.empty and Requests_Down.empty:
        print('All requests have been matched.')
        break
    
    if status == 'match' and not Offers.empty: # If there was at least a match with an unconditionnal request, try again on older bids
        general_status = 'match'
        while general_status == 'match': # As long as previous offers are matching, check for matches
            print('All Offers in SOB are being verified.')
            general_status = 'no match'
            for O in Offers.index:
                bid = Offers.loc[O].copy()
                offer_bus = nodes.index(bid.at['Bus'])
                offer_direction = bid.at['Direction']
                offer_price = bid.at['Price']
                offer_quantity = bid.at['Quantity']
                G, D, status, Social_Welfare, Requests_Up, Requests_Down, Offers , Accepted_Requests_Conditionnal = matching('old',G, D, Social_Welfare, O, offer_direction, offer_bus, offer_quantity, offer_price, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditionnal)
                if status == 'match':
                    general_status = 'match'
            if general_status == 'no match':
                print('No match was found.')
                
    # print('Requests_Up:')
    # print(Requests_Up)
    # print('Requests_Down:')
    # print(Requests_Down)
    # print('Offers:')
    # print(Offers)
    
    if Requests_Up.empty and Requests_Down.empty:
        print('All requests have been matched.')
        break
        

print('---------------------------------')
print('Social Welfare: {}'.format(round(Social_Welfare,2)))
