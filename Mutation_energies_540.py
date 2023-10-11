# -*- coding: utf-8 -*-
"""03 Random Multiple Iterator.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rBYWoh8EYjnbvKOJenMScvhs6QvkJmDy
"""

# Generates multiple random arrangements, and finds the one with the best power generated.
# Uses wind data for 2007. AEP caculation is same as given code, optimized to avoid redundant calculations in each iteration

# Module List
import numpy  as np
import pandas as pd                     
from   math   import radians as DegToRad       # Degrees to radians Conversion

from shapely.geometry import Point             # Imported for constraint checking
from shapely.geometry.polygon import Polygon

import warnings
warnings.filterwarnings("ignore")

def binWindResourceData(df):
    """
    Loads the wind data. Returns a 2D array with shape (36,15). 
    Each cell in  array is a wind direction and speed 'instance'. 
    Values in a cell correspond to probability of instance
    occurence.  
    """
   
    # Load wind data. Then, extracts the 'drct', 'sped' columns
    wind_resource = df[['drct', 'sped']].to_numpy(dtype = np.float32)
    
    # direction 'slices' in degrees
    slices_drct   = np.roll(np.arange(10, 361, 10, dtype=np.float32), 1)
    ## slices_drct   = [360, 10.0, 20.0.......340, 350]
    n_slices_drct = slices_drct.shape[0]
    
    # speed 'slices'
    slices_sped   = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 
                        18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0]
    n_slices_sped = len(slices_sped)-1

    
    # placeholder for binned wind
    binned_wind = np.zeros((n_slices_drct, n_slices_sped), 
                           dtype = np.float32)
    
    # 'trap' data points inside the bins. 
    for i in range(n_slices_drct):
        for j in range(n_slices_sped):     
            
            # because we already have drct in the multiples of 10
            foo = wind_resource[(wind_resource[:,0] == slices_drct[i])] 

            foo = foo[(foo[:,1] >= slices_sped[j]) 
                          & (foo[:,1] <  slices_sped[j+1])]
            
            binned_wind[i,j] = foo.shape[0]  
    
    wind_inst_freq   = binned_wind/np.sum(binned_wind)
    wind_inst_freq   = wind_inst_freq.ravel()
    
    return(wind_inst_freq)

def searchSorted(lookup, sample_array):
    """"Returns lookup indices for closest values w.r.t sample_array elements"""

    lookup_middles = lookup[1:] - np.diff(lookup.astype('f'))/2
    idx1 = np.searchsorted(lookup_middles, sample_array)
    indices = np.arange(lookup.shape[0])[idx1]
    return indices

def preProcessing(power_curve):
    """
    Doing preprocessing to avoid the same repeating calculations.
    Record the required data for calculations. Do that once.
    Data are set up (shaped) to assist vectorization. Used later in
    function totalAEP. 
    """
    # number of turbines
    n_turbs       =   50
    
    # direction 'slices' in degrees
    slices_drct   = np.roll(np.arange(10, 361, 10, dtype=np.float32), 1)
    ## slices_drct   = [360, 10.0, 20.0.......340, 350]
    n_slices_drct = slices_drct.shape[0]
    
    # speed 'slices'
    slices_sped   = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 
                        18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0]
    n_slices_sped = len(slices_sped)-1
    
    # number of wind instances
    n_wind_instances = (n_slices_drct)*(n_slices_sped)
    
    # Create wind instances. There are two columns in the wind instance array
    # First Column - Wind Speed. Second Column - Wind Direction
    # Shape of wind_instances (n_wind_instances,2). 
    # Values [1.,360.],[3.,360.],[5.,360.]...[25.,350.],[27.,350.],29.,350.]
    wind_instances = np.zeros((n_wind_instances,2), dtype=np.float32)
    counter = 0
    for i in range(n_slices_drct):
        for j in range(n_slices_sped): 
            
            wind_drct =  slices_drct[i]
            wind_sped = (slices_sped[j] + slices_sped[j+1])/2
            
            wind_instances[counter,0] = wind_sped
            wind_instances[counter,1] = wind_drct
            counter += 1

	# So that the wind flow direction aligns with the +ve x-axis.			
    # Convert inflow wind direction from degrees to radians
    wind_drcts =  np.radians(wind_instances[:,1] - 90)
    # For coordinate transformation 
    cos_dir = np.cos(wind_drcts).reshape(n_wind_instances,1)
    sin_dir = np.sin(wind_drcts).reshape(n_wind_instances,1)
    
    # create copies of n_wind_instances wind speeds from wind_instances
    wind_sped_stacked = np.column_stack([wind_instances[:,0]]*n_turbs)
   
    # Pre-prepare matrix with stored thrust coeffecient C_t values for 
    # n_wind_instances shape (n_wind_instances, n_turbs, n_turbs). 
    # Value changing only along axis=0. C_t, thrust coeff. values for all 
    # speed instances.
    # we use power_curve data as look up to estimate the thrust coeff.
    # of the turbine for the corresponding closest matching wind speed
    indices = searchSorted(power_curve[:,0], wind_instances[:,0])
    C_t     = power_curve[indices,1]
    # stacking and reshaping to assist vectorization
    C_t     = np.column_stack([C_t]*(n_turbs*n_turbs))
    C_t     = C_t.reshape(n_wind_instances, n_turbs, n_turbs)
    
    return(n_wind_instances, cos_dir, sin_dir, wind_sped_stacked, C_t)


    
def checkConstraints(turb_coords, turb_diam):
    """
    -**-THIS FUNCTION SHOULD NOT BE MODIFIED-**-
    
    Checks if the turbine configuration satisfies the two
    constraints:(i) perimeter constraint,(ii) proximity constraint 
    Prints which constraints are violated if any. Note that this 
    function does not quantifies the amount by which the constraints 
    are violated if any. 
    
    :called from
        main 
        
    :param
        turb_coords - 2d np array containing turbine x,y coordinates
        turb_diam   - Diameter of the turbine (m)
    
    :return
        None. Prints messages.   
    """
    bound_clrnc      = 50
    prox_constr_viol = False
    peri_constr_viol = False
    
    # create a shapely polygon object of the wind farm
    farm_peri = [(0, 0), (0, 4000), (4000, 4000), (4000, 0)]
    farm_poly = Polygon(farm_peri)
    
    # checks if for every turbine perimeter constraint is satisfied. 
    # breaks out if False anywhere
    for turb in turb_coords:
        turb = Point(turb)
        inside_farm   = farm_poly.contains(turb)
        correct_clrnc = farm_poly.boundary.distance(turb) >= bound_clrnc
        if (inside_farm == False or correct_clrnc == False):
            peri_constr_viol = True
            break
    
    # checks if for every turbines proximity constraint is satisfied. 
    # breaks out if False anywhere
    for i,turb1 in enumerate(turb_coords):
        for turb2 in np.delete(turb_coords, i, axis=0):
            if  np.linalg.norm(turb1 - turb2) < 4*turb_diam:
                prox_constr_viol = True
                break
    
    # print messages
    if  peri_constr_viol  == True  and prox_constr_viol == True:
          print('Somewhere both perimeter constraint and proximity constraint are violated\n')
    elif peri_constr_viol == True  and prox_constr_viol == False:
          print('Somewhere perimeter constraint is violated\n')
    elif peri_constr_viol == False and prox_constr_viol == True:
          print('Somewhere proximity constraint is violated\n')
    #else: print('Both perimeter and proximity constraints are satisfied !!\n')
        
    return()

def getAEP(turb_rad, turb_coords, power_curve, wind_inst_freq, 
            n_wind_instances, cos_dir, sin_dir, wind_sped_stacked, C_t):
    
    """
    Calculates AEP of the wind farm. Vectorised version.
    """
    # number of turbines
    n_turbs        =   turb_coords.shape[0]
    assert n_turbs ==  50, "Error! Number of turbines is not 50."
    
    # Prepare the rotated coordinates wrt the wind direction i.e downwind(x) & crosswind(y) 
    # coordinates wrt to the wind direction for each direction in wind_instances array
    rotate_coords   =  np.zeros((n_wind_instances, n_turbs, 2), dtype=np.float32)
    # Coordinate Transformation. Rotate coordinates to downwind, crosswind coordinates
    rotate_coords[:,:,0] =  np.matmul(cos_dir, np.transpose(turb_coords[:,0].reshape(n_turbs,1))) - \
                           np.matmul(sin_dir, np.transpose(turb_coords[:,1].reshape(n_turbs,1)))
    rotate_coords[:,:,1] =  np.matmul(sin_dir, np.transpose(turb_coords[:,0].reshape(n_turbs,1))) +\
                           np.matmul(cos_dir, np.transpose(turb_coords[:,1].reshape(n_turbs,1)))
 
    
    # x_dist - x dist between turbine pairs wrt downwind/crosswind coordinates)
    # for each wind instance
    x_dist = np.zeros((n_wind_instances,n_turbs,n_turbs), dtype=np.float32)
    for i in range(n_wind_instances):
        tmp = rotate_coords[i,:,0].repeat(n_turbs).reshape(n_turbs, n_turbs)
        x_dist[i] = tmp - tmp.transpose()
    

    # y_dist - y dist between turbine pairs wrt downwind/crosswind coordinates)
    # for each wind instance    
    y_dist = np.zeros((n_wind_instances,n_turbs,n_turbs), dtype=np.float32)
    for i in range(n_wind_instances):
        tmp = rotate_coords[i,:,1].repeat(n_turbs).reshape(n_turbs, n_turbs)
        y_dist[i] = tmp - tmp.transpose()
    y_dist = np.abs(y_dist) 
     

    # Now use element wise operations to calculate speed deficit.
    # kw, wake decay constant presetted to 0.05
    # use the jensen's model formula. 
    # no wake effect of turbine on itself. either j not an upstream or wake 
    # not happening on i because its outside of the wake region of j
    # For some values of x_dist here RuntimeWarning: divide by zero may occur
    # That occurs for negative x_dist. Those we anyway mark as zeros. 
    sped_deficit = (1-np.sqrt(1-C_t))*((turb_rad/(turb_rad + 0.05*x_dist))**2) 
    sped_deficit[((x_dist <= 0) | ((x_dist > 0) & (y_dist > (turb_rad + 0.05*x_dist))))] = 0.0
    
    
    # Calculate Total speed deficit from all upstream turbs, using sqrt of sum of sqrs
    sped_deficit_eff  = np.sqrt(np.sum(np.square(sped_deficit), axis = 2))

    
    # Element wise multiply the above with (1- sped_deficit_eff) to get
    # effective windspeed due to the happening wake
    wind_sped_eff     = wind_sped_stacked*(1.0-sped_deficit_eff)

    
    # Estimate power from power_curve look up for wind_sped_eff
    indices = searchSorted(power_curve[:,0], wind_sped_eff.ravel())
    power   = power_curve[indices,2]
    power   = power.reshape(n_wind_instances,n_turbs)
    
    # Farm power for single wind instance 
    power   = np.sum(power, axis=1)
    
    # multiply the respective values with the wind instance probabilities 
    # year_hours = 8760.0
    AEP = 8760.0*np.sum(power*wind_inst_freq)
    
    # Convert MWh to GWh
    AEP = AEP/1e3
    
    return(AEP)

power_curve = pd.read_csv('power_curve.csv', sep=',', dtype = np.float32).to_numpy()
df_winddata = pd.read_csv('wind_data_combined.csv')

main_turb_specs    =  { 'Name': 'Anon Name', 'Vendor': 'Anon Vendor', 'Type': 'Anon Type', 'Dia (m)': 100, 'Rotor Area (m2)': 7853, 'Hub Height (m)': 100, 'Cut-in Wind Speed (m/s)': 3.5, 'Cut-out Wind Speed (m/s)': 25, 'Rated Wind Speed (m/s)': 15, 'Rated Power (MW)': 3 }
main_turb_diam      =  main_turb_specs['Dia (m)']
main_turb_rad       =  main_turb_diam/2 

main_wind_inst_freq =  binWindResourceData(df_winddata)  
main_n_wind_instances, main_cos_dir, main_sin_dir, main_wind_sped_stacked, main_C_t = preProcessing(power_curve)

import pandas as pd
import math
import random
import matplotlib.pyplot as plt
import winsound

frequency = 1000  # Set Frequency To 2500 Hertz
duration = 1000  # Set Duration To 1000 ms == 1 second

no_of_turbines = 50
mu = 50
iteration = 0
x = 0.9
c = 40
iterations = 2000
Dm = 400
tries_retaining_parents = 50
tries_changing_parents = 20

def generate_random_locations():
    X_values = [0 for i in range(no_of_turbines)]
    Y_values = [0 for i in range(no_of_turbines)]
    df = pd.DataFrame()
    df['x'] = X_values
    df['y'] = Y_values
    x = random.uniform(50, 3950)
    y = random.uniform(50, 3950)
    df.iloc[0] = [x, y]
    for i in range(1, 50):
        x = random.uniform(50, 3950)
        y = random.uniform(50, 3950)
        flag = 0
        while (flag == 0):
            flag = 1
            for j in range(0, i):
                if (dist(df, j, x, y) < 400):
                    flag = 0
                    break
            df.iloc[i] = [x, y]
            x = random.uniform(50, 3950)
            y = random.uniform(50, 3950)
    return df

def dist(df, i, p, q):
        x = df.iloc[i,0] - p
        y = df.iloc[i,1] - q
        dist = x**2 + y**2
        return (math.sqrt(dist))

def generateRandom(df):    
    x = random.randint(50, 3950)
    y = random.randint(50, 3950)
    df.iloc[0] = [x,y]
    for i in range(1,50):
        x = random.randint(50, 3950)
        y = random.randint(50, 3950)
        flag = 0
        while(flag == 0):
            flag = 1
            for j in range(0,i):
                if(dist(df, j, x, y) < 400):
                    flag = 0
                    break
            df.iloc[i] = [x,y]
            x = random.randint(50, 3950)
            y = random.randint(50, 3950)
    return(df)

def initialize_generation_by_mu_random_files(mu):
    file_names = []
    generation = []
    for i in range(mu):
        file_names.append('Arrangement_'+str(i)+'.csv')
    for i in range(mu):
        individual = []
        df = pd.read_csv(file_names[i])
        individual.append(df)
        individual.append(getAEP(main_turb_rad, df.to_numpy(dtype = np.float32),power_curve, main_wind_inst_freq, main_n_wind_instances, main_cos_dir,
               main_sin_dir, main_wind_sped_stacked, main_C_t))
        generation.append(individual)


    return generation

def initialize_generation(mu):
  generation=[]
  for i in range(mu):
    #if(i%1000==0): print(i)
    location_list=[]
    random_locations=generate_random_locations()
    location_aep=getAEP(main_turb_rad, random_locations.to_numpy(dtype = np.float32),power_curve, main_wind_inst_freq, main_n_wind_instances, main_cos_dir,
               main_sin_dir, main_wind_sped_stacked, main_C_t)
    location_list.append(random_locations)
    location_list.append(location_aep)
    generation.append(location_list)
  return generation

def mutation(generation_to_be_mutated,no_retained):
    for i in range(mu):
        pm1 = random.uniform(0, 2)
        generation_to_be_mutated[i].append(pm1)
        pm2 = []
        for epoch in range(no_of_turbines):
            pm2.append(random.uniform(0, 2))
        generation_to_be_mutated[i][0]['pm2'] = pm2

    rm1 = random.uniform(0, 1)
    rm2 = random.uniform(0, 1)

    for i in range(no_retained, mu):
        if rm1 < generation_to_be_mutated[i][2]:
            for turbine in range(no_of_turbines):
                flag = 1
                no_of_tries = 100
                while(flag == 1 and no_of_tries > 0):

                    rm3 = random.uniform(0, 1)
                    rm4 = random.uniform(0, 1)
                    rm5 = random.uniform(0, 1)
                    rm6 = random.uniform(0, 1)

                    if rm2 < generation_to_be_mutated[i][0].pm2[turbine]:
                        x = generation_to_be_mutated[i][0].x[turbine] + Dm * (rm3 - rm4)
                        y = generation_to_be_mutated[i][0].y[turbine] + Dm * (rm5 - rm6)
                        flag = 0
                        for epoch in range(no_of_turbines):
                            if math.sqrt((generation_to_be_mutated[i][0].x[epoch] - x) ** 2 + (
                                    generation_to_be_mutated[i][0].y[epoch] - y) ** 2) < 400:
                                flag = 1
                                break
                            if (x <= 50 or y <= 50 or x >= 3950 or y >= 3950):
                                flag = 1
                                break

                        if flag == 0:
                            if i < no_retained:
                                new_df = generation_to_be_mutated[i][0].copy()
                                new_df.x[turbine] = x
                                new_df.y[turbine] = y
                                if(generation_to_be_mutated[i][1] < getAEP(main_turb_rad, new_df.to_numpy(dtype = np.float32),power_curve, main_wind_inst_freq, main_n_wind_instances, main_cos_dir,
               main_sin_dir, main_wind_sped_stacked, main_C_t)):
                                    generation_to_be_mutated[i][0].x[turbine] = x
                                    generation_to_be_mutated[i][0].y[turbine] = y
                            else:
                                generation_to_be_mutated[i][0].x[turbine] = x
                                generation_to_be_mutated[i][0].y[turbine] = y

                    else:
                        flag = 0

                    no_of_tries -=1

    clear_probabilities(generation_to_be_mutated)

    for i in range(mu):
        generation_to_be_mutated[i][1] = getAEP(main_turb_rad, generation_to_be_mutated[i][0].to_numpy(dtype = np.float32),power_curve, main_wind_inst_freq, main_n_wind_instances, main_cos_dir,
               main_sin_dir, main_wind_sped_stacked, main_C_t)

def clear_probabilities(generation_to_be_cleared):
    for i in range(mu):
        generation_to_be_cleared[i].pop()
        #generation_to_be_cleared[i][0] = generation_to_be_cleared[i][0].drop(['pm2'],  axis=1)

def crossover(parents_for_crossovers):
    parents = random.sample(parents_for_crossovers, 2)
    X_values = [0 for i in range(no_of_turbines)]
    Y_values = [0 for i in range(no_of_turbines)]
    df = pd.DataFrame()
    df['x'] = X_values
    df['y'] = Y_values
    flag = 0
    while (flag == 0):
        flag = 1
        a = random.uniform(-5, 5)
        x = a * parents[0][0]['x'][0] + (1 - a) * parents[1][0]['x'][0]
        a = random.uniform(-5, 5)
        y = a * parents[0][0]['y'][0] + (1 - a) * parents[1][0]['y'][0]
        if (x <= 50 or y <= 50 or x >= 3950 or y >= 3950):
            flag = 0
    df.iloc[0] = [x, y]
    for i in range(1, 50):
        a = random.uniform(-5, 5)
        x = a * parents[0][0]['x'][i] + (1 - a) * parents[1][0]['x'][i]
        a = random.uniform(-5, 5)
        y = a * parents[0][0]['y'][i] + (1 - a) * parents[1][0]['y'][i]
        flag = 0
        iter_same_parents = 0
        iter_changing_parents = 0
        while (flag == 0):
            iter_same_parents = iter_same_parents + 1

            if (iter_changing_parents > tries_changing_parents):
                return generateRandom(df)

            if (iter_same_parents > tries_retaining_parents):
                iter_changing_parents += 1
                parents = random.sample(parents_for_crossovers, 2)
                iter_same_parents = 0

            flag = 1
            if (x <= 50 or y <= 50 or x >= 3950 or y >= 3950):
                flag = 0
            for j in range(0, i):
                if (dist(df, j, x, y) < 400):
                    flag = 0
                    break
            df.iloc[i] = [x, y]
            a = random.uniform(-5, 5)
            x = a * parents[0][0]['x'][i] + (1 - a) * parents[1][0]['x'][i]
            a = random.uniform(-5, 5)
            y = a * parents[0][0]['y'][i] + (1 - a) * parents[1][0]['y'][i]
    return df

# initialization
# main function
generation_zero = initialize_generation(mu)
#generation_zero = initialize_generation_by_mu_random_files(mu)
print(generation_zero)
parent_generation = generation_zero
solution_values = []


while (iteration < iterations):
    print('iteration : ', iteration)
    next_generation = []
    parent_generation.sort(key=lambda x: x[1], reverse=True)

    for epoch in range(math.floor(mu-mu*x)):
        next_generation.append(parent_generation[epoch])

    # crossover for offsprings
    parents_for_crossovers = []
    for epoch in range(math.floor(x * mu)):
        tournament_selection_candidates = random.sample(parent_generation, c)
        parents_for_crossovers.append(max(tournament_selection_candidates, key=lambda p: p[1]))
        number_of_offsprings = 0
    while (number_of_offsprings < x * mu):
        print('generating crossover')
        offspring = crossover(parents_for_crossovers)
        offspring_list = []
        offspring_list.append(offspring)
        offspring_aep = getAEP(main_turb_rad, offspring.to_numpy(dtype = np.float32),power_curve, main_wind_inst_freq, main_n_wind_instances, main_cos_dir,
               main_sin_dir, main_wind_sped_stacked, main_C_t)
        offspring_list.append(offspring_aep)
        next_generation.append(offspring_list)
        number_of_offsprings = number_of_offsprings + 1
    print('iteration complete')
    # MUTATION
    #print(next_generation)
    print('now mutation')
    next_generation.sort(key=lambda x: x[1], reverse=True)
    mutation(next_generation, 1)
    # MUTATION DONE
    parent_generation = next_generation
    solution_values.append(max(next_generation, key=lambda p: p[1]))
    print("Best solution from this generation is:", max(next_generation, key=lambda p: p[1]))
    if (iteration != 0):
        if(solution_values[iteration][1] < solution_values[iteration-1][1]):
            print("ALERT ALERT ALERT ALERT")
            winsound.Beep(frequency, duration)
    iteration = iteration + 1

for i in range(len(solution_values)):
    print('Iteration ', i, ' AEP =', solution_values[i][1])

max(next_generation, key=lambda p: p[1])[0].to_csv('sol.csv')

