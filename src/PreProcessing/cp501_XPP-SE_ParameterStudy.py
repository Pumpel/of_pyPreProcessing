'''
Created on Nov 2, 2017

@author: timo
'''

from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParameterFile import ParameterFile
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

import pandas as pd
import os

if __name__ == '__main__':
    
    #Test directory
    os.chdir("/media/timo/linuxSimData/NonNewtonian/cp501/cp501_wedgegrid003_XPP-SE_validationStudy/")
    wd = os.getcwd()
    
    
    #Importing the parameters from the csv file
    dataFrame = pd.read_csv('measuredData.csv', header=0)
    dataFrame.drop(0, axis=0, inplace=True)
    dataFrame.drop(list(range(4,25,1)), axis=0, inplace=True)
    print(dataFrame)
    
    #Loading the openFoam template case
    sol = SolutionDirectory("/media/timo/linuxSimData/NonNewtonian/cp501/2DWedge_grid003_templates/2DWedge_grid003_template_002")
    
    #Creating the cases for all parameters
    for measurePoint in dataFrame.Messpkt:
        caseName = "cp501_xpp-se_measurement_{}".format(measurePoint)
        print("Creating case: {}".format(caseName))
        
        #Clone the case and 
        currentCase = sol.cloneCase(os.path.join(wd, caseName))
        
        index = dataFrame.loc[measurePoint]
        
        file_U = os.path.join(currentCase.name, "0.0/U")
        file_viscProperties = os.path.join(currentCase.name, "constant/viscoelasticProperties")
        
        parsed_file_U = ParsedParameterFile(file_U)
        parsed_file_viscProperties = ParsedParameterFile(file_viscProperties)
        
        rheologyDict = parsed_file_viscProperties["rheology"]
        lambdaOb = rheologyDict.get('lambdaOb')
        lambdaOb[2]= 0.1401
        etaP = rheologyDict.get('etaP')
        etaP[2] = index.Viskosität 
        
        uTOPInletDict = parsed_file_U["boundaryField"].get('TOP')
        uTOPInletDict['omega'] = index.Kreisfrequenz_eqv

        parsed_file_U.writeFile()
        parsed_file_viscProperties.writeFile()
        
        
        