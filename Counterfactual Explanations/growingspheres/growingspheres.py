#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .utils.gs_utils import generate_ball, generate_sphere, generate_ring, get_distances
from itertools import combinations
import numpy as np
from sklearn.metrics.pairwise import pairwise_distances
from sklearn.utils import check_random_state



class GrowingSpheres:
    """
    class to fit the Original Growing Spheres algorithm
    
    Inputs: 
    obs_to_interprete: instance whose prediction is to be interpreded
    prediction_fn: prediction function, must return an integer label
    caps: min max values of the explored area. Right now: if not None, the minimum and maximum values of the 
    target_class: target class of the CF to be generated. If None, the algorithm will look for any CF that is predicted to belong to a different class than obs_to_interprete
    n_in_layer: number of observations to generate at each step # to do
    layer_shape: shape of the layer to explore the space
    first_radius: radius of the first hyperball generated to explore the space
    dicrease_radius: parameter controlling the size of the are covered at each step
    sparse: controls the sparsity of the final solution (boolean)
    verbose: text
    """
    def __init__(self,
                obs_to_interprete,
                prediction_fn,
                target_class=None,
                caps=None,
                n_in_layer=2000,
                layer_shape='ring',
                first_radius=0.1,
                dicrease_radius=10,
                sparse=True,
                verbose=False):
        """
        """
        self.obs_to_interprete = obs_to_interprete
        self.prediction_fn = prediction_fn
        self.y_obs = prediction_fn(obs_to_interprete.reshape(1, -1))
        
        #if target_class == None: #To change: works only for binary classification...
        #target_class = 1 - self.y_obs
        
        self.target_class = target_class
        self.caps = caps
        self.n_in_layer = n_in_layer
        self.first_radius = first_radius
        if dicrease_radius <= 1.0:
            raise ValueError("Parameter dicrease_radius must be > 1.0")
        else:
            self.dicrease_radius = dicrease_radius 

        self.sparse = sparse
        if layer_shape in ['ring', 'ball', 'sphere']:
            self.layer_shape = layer_shape
        else:
            raise ValueError("Parameter layer_shape must be either 'ring', 'ball' or 'sphere'.")
        
        self.verbose = verbose
        
        if int(self.y_obs) != self.y_obs:
            raise ValueError("Prediction function should return a class (integer)")

###################################MODIFICATION########################################
    def find_counterfactual(self, num_counterfactuals=10):
        counterfactuals = []
        unique_counterfactuals = set()  # Keep track of unique counterfactual instances
        ennemies_ = self.exploration()
        #print("Shape of layer:", ennemies_.shape)
        #print("Shape of obs_to_interprete:", self.obs_to_interprete.shape)
        
        # Sort the generated instances based on their distances to the original instance
        sorted_ennemies = sorted(ennemies_, 
                                key=lambda x: pairwise_distances(self.obs_to_interprete.reshape(1, -1), x.reshape(1, -1)))
        
        self.e_star = None  # Initialize e_star before the loop
        # Consider multiple closest instances beyond just the first one
        for k in range(min(num_counterfactuals, len(sorted_ennemies))):
            closest_ennemy_ = sorted_ennemies[k]

            self.e_star = closest_ennemy_

            if self.sparse:
                out = self.feature_selection(closest_ennemy_)
            else:
                out = closest_ennemy_

            # Check if the current counterfactual is unique
            if tuple(out) not in unique_counterfactuals:
                counterfactuals.append(out)
                unique_counterfactuals.add(tuple(out))
    
        # Check if no valid counterfactuals were found
        if not counterfactuals:
            return np.zeros_like(self.obs_to_interprete)
        
        return counterfactuals

#################################################################
    
    '''def find_counterfactual(self, num_counterfactuals=10):
        counterfactuals = []
        for _ in range(num_counterfactuals):
            ennemies_ = self.exploration()
            closest_ennemy_ = sorted(ennemies_, 
                                     key=lambda x: pairwise_distances(self.obs_to_interprete.reshape(1, -1), x.reshape(1, -1)))[0] 
            self.e_star = closest_ennemy_
            if self.sparse:
                out = self.feature_selection(closest_ennemy_)
            else:
                out = closest_ennemy_
            counterfactuals.append(out)
        return counterfactuals'''


    '''def find_counterfactual(self):
        """
        Finds the decision border then perform projections to make the explanation sparse.
        """
        ennemies_ = self.exploration()
        closest_ennemy_ = sorted(ennemies_, 
                                 key= lambda x: pairwise_distances(self.obs_to_interprete.reshape(1, -1), x.reshape(1, -1)))[0] 
        self.e_star = closest_ennemy_
        if self.sparse == True:
            out = self.feature_selection(closest_ennemy_)
        else:
            out = closest_ennemy_
        return out'''
    
#############################################MODIFICATION################################################
    def exploration(self):
        """
        Exploration of the feature space to find the decision boundary. Generation of instances in growing hyperspherical layers.
        """
        max_attempts = 100
        attempt = 0  
        n_ennemies_ = 999
        radius_ = self.first_radius
        
        while n_ennemies_ > 0 and attempt < max_attempts:
            
            first_layer_ = self.ennemies_in_layer_(radius=radius_, caps=self.caps, n=self.n_in_layer, first_layer=True)
            
            n_ennemies_ = first_layer_.shape[0]
            radius_ = radius_ / self.dicrease_radius  # Decrease the radius for the next iteration
            attempt += 1  # Increment the attempt counter
    
            if self.verbose:
                print("%d enemies found in initial hyperball." % n_ennemies_)
            
                if n_ennemies_ > 0:
                    print("Zooming in...")
        
        if attempt == max_attempts:
            if self.verbose:
                print("Maximum number of attempts reached. Returning zeros!")
            return np.zeros_like(self.obs_to_interprete)

        if self.verbose:
            print("Expanding hypersphere...")
    
        iteration = 0
        step_ = radius_ / self.dicrease_radius
    
        while n_ennemies_ <= 0 and iteration < max_attempts:  # Ensure we don't get stuck
            
            layer = self.ennemies_in_layer_(layer_shape=self.layer_shape, radius=radius_, step=step_, caps=self.caps,
                                            n=self.n_in_layer, first_layer=False)
                            
            n_ennemies_ = layer.shape[0]
            radius_ = radius_ + step_
            iteration += 1
        
        if attempt == max_attempts:
            if self.verbose:
                print("Maximum number of attempts reached. Returning zeros.")
            return np.zeros_like(self.obs_to_interprete)

    
        if self.verbose:
            print("Final radius: ", (radius_ - step_, radius_))
            print("Final number of enemies: ", n_ennemies_)
            print("Shape of layer:", layer.shape)
            print("Shape of obs_to_interprete:", self.obs_to_interprete.shape)
        
        return layer
######################################################################################

    '''def exploration(self):
        """
        Exploration of the feature space to find the decision boundary. Generation of instances in growing hyperspherical layers.
        """
        n_ennemies_ = 999
        radius_ = self.first_radius
        
        while n_ennemies_ > 0:
            
            first_layer_ = self.ennemies_in_layer_(radius=radius_, caps=self.caps, n=self.n_in_layer, first_layer=True)
            
            n_ennemies_ = first_layer_.shape[0]
            radius_ = radius_ / self.dicrease_radius # radius gets dicreased no matter, even if no enemy?

            if self.verbose == True:
                print("%d ennemies found in initial hyperball."%n_ennemies_)
            
                if n_ennemies_ > 0:
                    print("Zooming in...")
        else:
            if self.verbose == True:
                print("Expanding hypersphere...")

            iteration = 0
            step_ = radius_ / self.dicrease_radius
            #step_ = (self.dicrease_radius - 1) * radius_/5.0  #To do: work on a heuristic for these parameters
            
            while n_ennemies_ <= 0:

                layer = self.ennemies_in_layer_(layer_shape=self.layer_shape, radius=radius_, step=step_, caps=self.caps,
                                                n=self.n_in_layer, first_layer=False)
                                
                n_ennemies_ = layer.shape[0]
                radius_ = radius_ + step_
                iteration += 1
                
            if self.verbose == True:
                print("Final number of iterations: ", iteration)
        
        if self.verbose == True:
            print("Final radius: ", (radius_ - step_, radius_))
            print("Final number of ennemies: ", n_ennemies_)
        return layer'''
    
    
    def ennemies_in_layer_(self, layer_shape='ring', radius=None, step=None, caps=None, n=1000, first_layer=False):
        """
        Basis for GS: generates a hypersphere layer, labels it with the blackbox and returns the instances that are predicted to belong to the target class.
        """
        # todo: split generate and get_enemies

        if first_layer:
            layer = generate_ball(self.obs_to_interprete, radius, n)
        
        else:
        
            if self.layer_shape == 'ring':
                segment = (radius, radius + step)
                layer = generate_ring(self.obs_to_interprete, segment, n)
            
            elif self.layer_shape == 'sphere':
                layer = generate_sphere(self.obs_to_interprete, radius + step, n)
                
            elif self.layer_shape == 'ball':
                layer = generate_ball(self.obs_to_interprete, radius + step, n)

        #cap here: not optimal - To do
        if caps != None:
            cap_fn_ = lambda x: min(max(x, caps[0]), caps[1])
            layer = np.vectorize(cap_fn_)(layer)
            
        preds_ = self.prediction_fn(layer)
        
        if self.target_class == None:
            enemies_layer = layer[np.where(preds_ != self.y_obs)]
        else:
            enemies_layer = layer[np.where(preds_ == self.target_class)]
            
        return enemies_layer
    
    
    def feature_selection(self, counterfactual):
        """
        Projection step of the GS algorithm. Make projections to make (e* - obs_to_interprete) sparse. Heuristic: sort the coordinates of np.abs(e* - obs_to_interprete) in ascending order and project as long as it does not change the predicted class
        
        Inputs:
        counterfactual: e*
        """
        if self.verbose == True:
            print("Feature selection...")
            
        move_sorted = sorted(enumerate(abs(counterfactual - self.obs_to_interprete.flatten())), key=lambda x: x[1])
        move_sorted = [x[0] for x in move_sorted if x[1] > 0.0]
        
        out = counterfactual.copy()
        
        reduced = 0
        
        for k in move_sorted:
        
            new_enn = out.copy()
            new_enn[k] = self.obs_to_interprete.flatten()[k]

            if self.target_class == None:
                condition_class = self.prediction_fn(new_enn.reshape(1, -1)) != self.y_obs
                
            else:
                condition_class = self.prediction_fn(new_enn.reshape(1, -1)) == self.target_class
                
            if condition_class:
                out[k] = new_enn[k]
                reduced += 1
                
        if self.verbose == True:
            print("Reduced %d coordinates"%reduced)
        return out

    
    def feature_selection_all(self, counterfactual):
        """
        Try all possible combinations of projections to make the explanation as sparse as possible. 
        Warning: really long!
        """
        if self.verbose == True:
            print("Grid search for projections...")
        for k in range(self.obs_to_interprete.size):
            print('==========', k, '==========')
            for combo in combinations(range(self.obs_to_interprete.size), k):
                out = counterfactual.copy()
                new_enn = out.copy()
                for v in combo:
                    new_enn[v] = self.obs_to_interprete[v]
                if self.prediction_fn(new_enn.reshape(1, -1)) == self.target_class:
                    print('bim')
                    out = new_enn.copy()
                    reduced = k
        if self.verbose == True:
            print("Reduced %d coordinates"%reduced)
        return out
    
    
    
class DirectedGrowingSpheres: # Warning: Not finished, do not use
    """
    class to fit the Original Growing Spheres algorithm
    """
    def __init__(self,
                obs_to_interprete,
                prediction_fn,
                target_class=None,
                caps=None,
                n_in_layer=10000, #en vrai n_in_layer depend de rayon pour garantir meme densite?
                first_radius=0.1,
                dicrease_radius=5):
        """
        """
        self.obs_to_interprete = obs_to_interprete
        self.prediction_fn = prediction_fn
        y_class = int(prediction_fn(obs_to_interprete.reshape(1, -1))[0][1] > 0.5) #marche que pour 2 classes là. en vrai sinon il faut prendre l'argmax
        self.y_obs = prediction_fn(obs_to_interprete.reshape(1, -1))[0][1]
        
        #if target_class == None:
        #    target_class = 1 - self.y_obs
        #self.target_class = target_class
        self.target_class = 1  - y_class
        
        self.caps = caps
        self.n_in_layer = n_in_layer
        self.first_radius = first_radius
        self.dicrease_radius = dicrease_radius

        
    def find_counterfactual(self): #nul
        ennemies_ = self.exploration()
        closest_ennemy_ = sorted(ennemies_, 
                                 key= lambda x: pairwise_distances(self.obs_to_interprete.reshape(1, -1), x.reshape(1, -1)))[0] 
        out = self.feature_selection(closest_ennemy_)
        return out
    
    
    def exploration(self):
        n_ennemies_ = 999
        radius_ = self.first_radius
        iteration = 0
        
        while n_ennemies_ > 0: #initial step idem: on veut une sphère qui n'a pas d'ennemi (pas le plus smart; peut être garder les derniers ennemis serait intelligent... bref
            first_layer_, y_layer_ = self.layer_with_preds(self.obs_to_interprete, radius_, self.caps, self.n_in_layer)
            n_ennemies_ = first_layer_[np.where(y_layer_ > 0.5)].shape[0] #IMPORTANT; PAREIL NE MARCHE QUE POUR CLASSIF BINAIRE. IL FAUDRA REPENSER CA POUR MULTILCASSE
            if iteration != 0:
                radius_ = radius_ / self.dicrease_radius #IMPORTANT: Le Dicrease devrait pouvoir se faire en fonction du nombre d'ennemis trouves: si beaucoup, on peut reduire de plus que si 3 ennemis.
                print("%d ennemies found in initial sphere. Zooming in..."%n_ennemies_)
            iteration += 1
            
        else:
            print("Exploring...")
            iteration = 0
            step_ = 0.1# (self.dicrease_radius - 1) * radius_/10.0 #a chabger
            #initialisation
            center_ = self.obs_to_interprete
            #layer = first_layer_
            layer, y_layer_ = self.layer_with_preds(self.obs_to_interprete, radius_*5, self.caps, self.n_in_layer)
            self.centers = []
            radius_ = radius_ #bluff
            while n_ennemies_ <= 0:                
                gradient = self.get_exploration_direction(layer, y_layer_) #la on fait comme s'il n'y avait qu'un gradient mais il pourrait y en avoir plusieurs
                center_ = center_ + gradient * step_ #idem
                layer, y_layer_ = self.layer_with_preds(center_, radius_*5, self.caps, self.n_in_layer)
                self.centers.append(center_)
                n_ennemies_ = layer[np.where(y_layer_ > 0.5)].shape[0] #proba d'appartenir à la nouvelle classe
                iteration += 1
                
            print("Final number of iterations: ", iteration)
        print("Final radius: ", (radius_ - step_, radius_))
        print("Final number of ennemies: ", n_ennemies_)
        self.centers = np.array(self.centers)
        return layer[np.where(y_layer_ > 0.5)] #proba d'appartenir à la nouvelle classe
    
    
    def layer_with_preds(self, center, radius, caps=None, n=1000):
        """
        prend obs, genere couche dans sphere, et renvoie les probas d'appartenir à target class
        """
        layer = generate_inside_ball(center, (0, radius), n)
        #cap here: pas optimal, ici meme min et meme max pour toutes variables;
        
        if caps != None:
            cap_fn_ = lambda x: min(max(x, caps[0]), caps[1])
            layer = np.vectorize(cap_fn_)(layer)
            
        preds = self.prediction_fn(layer)[:, self.target_class]
        return layer, preds
    
    def get_exploration_direction(self, layer, preds):
        from sklearn.linear_model import LinearRegression
        lr = LinearRegression(fit_intercept=True).fit(layer, preds)
        gradient = lr.coef_
        gradient = gradient / sum([x**2 for x in gradient])**(0.5)
        return gradient
    
    def get_exploration_direction2(self, layer, preds):
        return layer[np.where(preds == preds.max())][0] - self.obs_to_interprete
    
    
    
    def feature_selection(self, counterfactual): #checker
        """
        """
        print("Feature selection...")
        move_sorted = sorted(enumerate(abs(counterfactual - self.obs_to_interprete)), key=lambda x: x[1])
        move_sorted = [x[0] for x in move_sorted if x[1] > 0.0]
        out = counterfactual.copy()
        reduced = 0
        
        for k in move_sorted:
            new_enn = out.copy()
            new_enn[k] = self.obs_to_interprete[k]
            
            if self.prediction_fn(new_enn.reshape(1, -1))[0][self.target_class] > 0.5: #il faut mettre argmax pour multiclasse
                out[k] = new_enn[k]
                reduced += 1
                
        print("Reduced %d coordinates"%reduced)
        return out

 
    