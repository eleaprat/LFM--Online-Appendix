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

#%% Case data

SetPoint = [1.21,-0.04,-0.07,-0.14,-0.04,-0.14,-0.14,-0.07,-0.07,-0.04,-0.14,-0.07,-0.04,-0.07,-0.14] # Baseline injections at each node (negative for retrieval)

data  = system_input(SetPoint) # Retrieve all information of the network for this setpoint

nodes = data['nodes']                 # index for nodes

# Upload requests and offers
Requests = pd.read_csv('requests.csv')
all_bids = pd.read_csv('offers.csv')

# Separate requests for upward and downward flexibility
Requests_Up = Requests[(Requests.Direction == 'Up')]
Requests_Down = Requests[(Requests.Direction == 'Down')]

# Create an empty dataframe to contain the offers that were not matched (order book)
Offers = pd.DataFrame(columns = ['Bus','Direction','Quantity','Price'])
# Create an empty dataframe to contain the accepted conditional requests
Accepted_Requests_Conditional = pd.DataFrame(columns = ['Bus','Direction','Dispatch Change'])

# Initialize the social welfare calculation
Social_Welfare = 0

#%% Function to match an offer
def matching(bid_type, SetPoint, Social_Welfare, offer_index, offer, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional):
    
    epsilon = 0.00001 # Tolerance
    status = 'no match' # Marker to identify if there was a match with unconditional requests or not (if so, the order book should be checked for new matches)
    PTDF_calc = 0 # Counter of PTDF calculations performed (number of times the function PTDF_check is called)
    
    offer_bus = nodes.index(offer.at['Bus'])
    offer_direction = offer.at['Direction']
    offer_price = offer.at['Price']
    offer_quantity = offer.at['Quantity']
    
# Choose the proper requests to look into
    if offer_direction == 'Up':
        Requests = Requests_Up
        
    elif offer_direction == 'Down':
        Requests = Requests_Down
    
# Make sure that there are requests left to be matched
    if Requests.empty:
        print('All requests {} have already been matched.'.format(offer_direction))
        return SetPoint, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional

# Check matching with all the requests (in the same direction)
    for R in Requests.index:
        
        # Make sure that the prices are matching
        if offer_price <= Requests.at[R,'Price']:
            
            request_bus = nodes.index(Requests.at[R,'Bus'])
            Offered = offer_quantity
            Requested = Requests.at[R,'Quantity']
            Quantity = min(Offered,Requested) # Initially, the maximum quantity that can be exchanged is the minimum of the quantities of the bids
            # Check for this request only
            Quantity = PTDF_check(SetPoint,Quantity,offer_bus,request_bus,offer_direction) # Returns the maximum quantity that can be exchanged without leading to congestions
            PTDF_calc+=1 # Increment the counter of PTDF calculations performed
            
            # If this request alone is feasible, check all combinations with previously accepted conditional requests
            if Quantity > epsilon and not Accepted_Requests_Conditional.empty:
                # Create all combinations
                cond_requests = list(Accepted_Requests_Conditional.index) # List of accepted conditional requests, identified by their index in the dataframe
                comb=[] # List for all combinations of accepted conditional requests with the request under evaluation
                # Code to create all combinations
                for i in range(len(cond_requests)):
                    new_comb = [list(l) for l in combinations(cond_requests,i+1)]
                    for n in new_comb:
                        comb.append(n)
                        
                # Remove combinations for up and down regulation at the same bus
                for ra in range(len(Accepted_Requests_Conditional.index)-1):
                    first = Accepted_Requests_Conditional.index[ra]
                    second = Accepted_Requests_Conditional.index[ra+1]
                    if Accepted_Requests_Conditional.at[first,'Bus'] == Accepted_Requests_Conditional.at[second,'Bus'] and Accepted_Requests_Conditional.at[first,'Direction'] != Accepted_Requests_Conditional.at[second,'Direction']:
                        for c in comb:
                            if first in c and second in c:
                                comb.remove(c)
                                
                print('Number of combinations: {}'.format(len(comb)))
                
                # PTDF check for all combinations
                for c in comb:
                    if Quantity > epsilon: # If the quantity is still above zero
                        SetPoint_new = SetPoint
                        for i in c: # Update the setpoint with all the corresponding requests and matching offers
                            SetPoint_new = list(map(add,Accepted_Requests_Conditional.at[i,'Dispatch Change'],SetPoint_new))
                        Quantity = PTDF_check(SetPoint_new,Quantity,offer_bus,request_bus,offer_direction)
                        PTDF_calc+=1 # Increment the counter of PTDF calculations performed
                    else: # If the quantity is less than zero, the calculation can stop for this request: the match is unfeasible
                        break
            
            if Quantity > epsilon: # Line constraints are respected
                print('Offer {} ({}, bus {}) matched with Request {} ({}, bus {}) for a quantity of {} MW'.format(offer_index,offer_direction,nodes[offer_bus],R,offer_direction,Requests['Bus'][R],round(Quantity,3)))
               
                # Calculate the new value of the social welfare
                Social_Welfare += Quantity * (Requests.at[R,'Price'] - offer_price)
                
                # Calculate the corresponding changes in the setpoint
                Delta = [0] * len(SetPoint)
                if offer_direction == 'Up':
                    Delta[offer_bus]+=Quantity
                    Delta[request_bus]-=Quantity
                elif offer_direction == 'Down':
                    Delta[offer_bus]-=Quantity
                    Delta[request_bus]+=Quantity
                    
                # If the accepted request is unconditional, modify the setpoint and update the status marker
                if Requests.at[R,'Type'] == 'Unconditional':
                    SetPoint = list(map(add,SetPoint,Delta))
                    status = 'match'
                    
                elif Requests.at[R,'Type'] == 'Conditional':
                    # Check if request is already in the dataframe of accepted requests
                    if R in Accepted_Requests_Conditional.index:
                        # If so, update the corresponding dispatch change to inlcude the new offer
                        Delta_init = Accepted_Requests_Conditional.at[R,'Dispatch Change']
                        Delta_init = list(map(add,Delta_init,Delta))
                        Accepted_Requests_Conditional.at[R,'Dispatch Change'] = Delta_init
                    # If not, create a new entry in the dataframe
                    else:
                        Accepted_Requests_Conditional.loc[R]=[Requests.at[R,'Bus'], offer_direction, Delta]
                        Accepted_Requests_Conditional.sort_values(by=['Bus'], inplace=True) # Reorganize to group requests per node for the elimination of combinations with up and down requests at the same bus
                
                # Update quantities of these offer and request
                offer_quantity = Offered - Quantity
                Requests.at[R,'Quantity'] = Requested - Quantity
                if Requests.at[R,'Quantity'] < epsilon: # If the request was completely matched
                    Requests = Requests.drop([R], axis=0)
                # Update the corresponding dataframes
                    if offer_direction == 'Up':
                        Requests_Up = Requests_Up.drop([R], axis=0)
                    elif offer_direction == 'Down':
                        Requests_Down = Requests_Down.drop([R], axis=0)
                else:
                    if offer_direction == 'Up':
                        Requests_Up.at[R,'Quantity'] = Requested - Quantity
                    elif offer_direction == 'Down':
                        Requests_Down.at[R,'Quantity'] = Requested - Quantity
                        
                if offer_quantity < epsilon: # If the offer was completely matched
                    if bid_type == 'new':
                        print('{} PTDF verifications have been performed'.format(PTDF_calc))
                    elif bid_type == 'old': # In the case of checking the bids in the order book, the corresponding row must be dropped
                        Offers = Offers.drop([offer_index], axis=0)
                    return SetPoint, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional
            else:
                print('Offer {} ({}, bus {}) cannot match with Request {} ({}, bus {}) due to line congestions.'.format(offer_index,offer_direction,nodes[offer_bus],R,offer_direction,Requests['Bus'][R]))
        else:
            print('There are no requests matching Offer {} ({}, bus {}) in terms of price.'.format(offer_index,offer_direction,nodes[offer_bus]))
            break
    if offer_quantity > epsilon: # If the offer was not completely matched after trying all requests, update and order the book
        Offers.loc[offer_index]=[nodes[offer_bus],offer_direction,offer_quantity,offer_price]
        Offers.sort_values(by=['Price'], ascending=True, inplace=True)
    
    print('{} PTDF verifications have been performed'.format(PTDF_calc))
    return SetPoint, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional


#%% Check the power flows using PTDFs each time an offer is added

for b in all_bids.index:
    
    print('------ Betting round nb {} ------ '.format(b+1))
    
    new_bid = all_bids.loc[b].copy()
    print('New bid: ({}, {}, {}, {})'.format(new_bid.at['Bus'],new_bid.at['Direction'],round(new_bid.at['Quantity'],3),new_bid.at['Price']))
    
    start_time = time.time()
    SetPoint, status, Social_Welfare, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional = matching('new',SetPoint, Social_Welfare, b, new_bid, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional)
    duration=time.time()-start_time
    print('Computation time: {}s'.format(round(duration,3)))
    
    if Requests_Up.empty and Requests_Down.empty:
        print('All requests have been matched.')
        break
    
    # If there was at least a match with an unconditional request, try again on older bids
    if status == 'match' and not Offers.empty:
        general_status = 'match'
        while general_status == 'match': # As long as previous offers are matching with unconditional requests, check for matches
            print('All Offers in SOB are being verified.')
            general_status = 'no match'
            for O in Offers.index:
                bid = Offers.loc[O].copy()
                SetPoint, status, Social_Welfare, Requests_Up, Requests_Down, Offers , Accepted_Requests_Conditional = matching('old',SetPoint, Social_Welfare, O, bid, Requests_Up, Requests_Down, Offers, Accepted_Requests_Conditional)
                if status == 'match':
                    general_status = 'match'
            if general_status == 'no match':
                print('No match was found.')
    
    if Requests_Up.empty and Requests_Down.empty:
        print('All requests have been matched.')
        break
        
    print()

print()
print('---------------------------------')
print('Social Welfare: {}'.format(round(Social_Welfare,2)))
