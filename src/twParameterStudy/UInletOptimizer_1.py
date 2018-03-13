
from PatchPostProcessing import PatchAverage, PatchMagnitude
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

import os
import subprocess
import shutil

class Vector(object):
    
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z
        
    def __str__(self):
        return "({} {} {})".format(self.x, self.y, self.z)


class UInletOptimizer(object):


    def __init__(self, 
                 studyName="Study000",
                 workingDirectory=None,
                 studyTemplate=None,
                 maxIters=4,
                 Ugoal=None,
                 residual=None,
                 T1_p_Lbound=None,
                 T1_p_Ubound=None,
                 relDistToBound=0.03):
        
        # Folder name for the study. Simulations are stored in a folder with this name
        self.studyName = studyName
        # Template study to be used for the study. The template gets copied, only then
        # the copy is modified.
        self.studyTemplate = studyTemplate
        # The working directy is the directy, where the 'studyName' folder will be created
        self.cwd = workingDirectory
        # Changing to the working directory and creating the study
        self.prepareFolders()
        # Creating the pyFoam representation of the template case
        self.sol = SolutionDirectory(self.studyTemplate)
        
        self.iteration = 0
        self.maxIters = maxIters
        self.Ugoal = Ugoal
        self.residual = residual
        self.T1_p_Lbound = T1_p_Lbound
        self.T1_p_Ubound = T1_p_Ubound
        self.relDistToBound = relDistToBound
        
        # The simulationsDict holds the names of all simulations as keys and 
        # stores a pandas data frame with all relevant simulation results as the values
        self.simulationsDict = dict()
        self.t1new = None
        #self.newDeltaPDomain = 25
        #self.targetSigma = 0.8


        # Variables for the Patch calculations
        self.p_outlet = None
        self.p_inlet = None
        self.U_inlet_mag = None
        self.U_inlet_avgmag = None




    def prepareFolders(self):
        os.chdir(self.cwd)
        os.mkdir(self.studyName)
        self.studyWorkingDirectory = self.cwd + self.studyName

    # Here, custom intial values for the copied template case may be 
    # defined
    def setInitialValues(self,case, U, p, prgh):
        parsedU = os.path.join(case.name, "0.000000/U")
        parsedU = ParsedParameterFile(parsedU)
        #p
        parsedP = os.path.join(case.name, "0.000000/p")
        parsedP = ParsedParameterFile(parsedP)
        #prgh
        parsedPrgh = os.path.join(case.name, "0.000000/p_rgh")
        parsedPrgh = ParsedParameterFile(parsedPrgh)
   
        parsedU["internalField"] = "uniform " + U.__str__()
        parsedP["internalField"] = "uniform " + str(p)
        parsedPrgh["internalField"] = "uniform " + str(prgh)
        
        parsedU.writeFile()
        parsedP.writeFile()
        parsedPrgh.writeFile()
    
    # Definitions:
    # The table is the dictionary object obtained from the parsed 
    # parameter file
    # The table is read from the parsed parameter file and the entries are stored
    # as a list:
    # ['table', [ [x1, y1], [x2,y2], ... ] ]

    # This functions adds the value deltaT to all x-values (i.e. times) GREATER
    # the given tStart value in the provided table
    def addDTInTable(self, deltaT, tStart, table):
        table = table[1]
        for i in range(len(table)):
            if table[i][0] > tStart:
                table[i][0] = table[i][0] + deltaT
        return table
    
    # This function replaces every y-entry equal to the variable value with
    # the new variable value_n
    def changeAllValuesInTable(self, value, value_n, table):
        table = table[1]
        for i in range(len(table)):
            if table[i][1] == value:
                table[i][1] = value_n
        return table

    # This function changes only the second x-value of the given table
    def changeT1(self, value_n, table):
        table = table[1]
        for i in range(len(table)):
            if i == 1:
                table[i][0] = value_n
        return ('table', table)

    def getT1Value(self, table):
        table = table[1]
        res = None
        for i in range(len(table)):
            if i == 1:
                res = table[i][0]
        return res
    
    # Bounds the t1new value according to the lower bound and upper bound with
    # a rel distant the the bounds
    def biDirectionalBounding(self, t1new, bound_l, bound_u, relDistToBounds):
        relD = relDistToBounds
        # The new T1 value cannot be equal to his bounding values. 
        # Doing so, yields a non-valid table for the BC in question
        return max((bound_l+bound_u*relD), min((bound_u-bound_u*relD), t1new))

    # Modify this function to suite the specific OpenFOAM case
    def runBashCommands(self, currentCase):
        try:
            os.chdir(currentCase.name)
            #Running the simulation
            subprocess.call("cd ${0%/*} || exit 1", shell=True)
            subprocess.call(". $WM_PROJECT_DIR/bin/tools/RunFunctions", shell=True)
            #subprocess.call("rm -vf log.decomposePar; rm -rf processor*", shell=True)
            #subprocess.call(['cp', '-r', '0.000000.orig', '0.000000'], shell=True)
            subprocess.call('decomposePar -latestTime > log.decomposePar', shell=True)
            subprocess.call("mpirun -np 4 compMultiphaseCavitation -parallel > log.run1", shell=True)
            subprocess.call('reconstructPar -newTimes > log.reconstructPar', shell=True)
            #subprocess.call("rm -v log.reconstructPar; rm -rf processor*, shell=True)
        except:
            print("Error while executing the OpenFOAM commands")
        

    # Calling this function sets of the calculation    
    def run(self):
        print("Running main loop for a maximum of {} iterations".format(self.maxIters))
        while (self.iteration < self.maxIters and self.residual > 0.001): 
            #The residual calculation doesnt mean shit yet. 
            # Leave it out to avoid unexpected behaviour
            
            
            os.chdir(self.studyWorkingDirectory)
            # Create the case name based on the current iteration
            caseName = "sim" + str(self.iteration)

            # Cloning the template case to a folder name caseName
            cloneCasePath = os.path.join(self.studyWorkingDirectory, caseName)
            currentCase = self.sol.cloneCase(cloneCasePath)
            # Copying the run file manually, cause pyFoam doensnt do it by default
            shutil.copyfile(self.studyTemplate + "/run", cloneCasePath + "/run")
            os.chdir(currentCase.name)

            # Parsing the prgh file
            parsedPrgh = os.path.join(currentCase.name, "0.000000/p_rgh")
            parsedPrgh = ParsedParameterFile(parsedPrgh)
            prghTable = parsedPrgh["boundaryField"]["Inlet"]["uniformValue"]

            ##################################################################
            # Two simulations are performed first, to obtain two data points.
            # From there, the new time values of the table are calculated
            # by linear interpolation.
            ##################################################################

            #first simulation
            if self.iteration == 0:
                t1new = self.getT1Value(prghTable)
            #second simulation
            elif self.iteration == 1:
                sim0 = "sim" + str(0)
                Ulist0 = self.simulationsDict[sim0]["magU_in"].tolist()
                u1 = Ulist0[-1]
                u2 = self.Ugoal
                # Getting the time value of the first simulation
                t1 = self.simulationsDict[sim0]["t1new"].tolist()[-1]
                
                # Check if the value of sim1 is lower than the goal. If true, choose the new time
                # greater than the old one. If false, use a time lower than the old time
                if u1 < self.Ugoal:
                    t2 = t1 + t1/10
                else:
                    t2 = t1 - t1/10
                    
                Dt21 = t2- t1
                DU21 = u2 - u1
                if DU21 != 0.0:
                    # Interpolating the new time based on the goal time. 
                    # Mathematically this is bogus, but it yields a reasonable t1 value
                    # for the second simulation
                    t1new = t2 + (Dt21)/(DU21) * (self.Ugoal-u2)
                    t1new = self.biDirectionalBounding(t1new, 
                                                       self.T1_p_Lbound, 
                                                       self.T1_p_Ubound, 
                                                       self.relDistToBound)
                else:
                    t1new = t2
            # All following simulations
            elif self.iteration >= 1:
                # Reading in the U,T1 values for the last to simulations
                sim1 = "sim" + str((self.iteration - 2))
                sim2 = "sim" + str((self.iteration - 1))
                Ulist1 = self.simulationsDict[sim1]["magU_in"].tolist()
                Ulist2 = self.simulationsDict[sim2]["magU_in"].tolist()
                u1 = Ulist1[-1]
                u2 = Ulist2[-1]
                t1 = self.simulationsDict[sim1]["t1new"].tolist()[-1]
                t2 = self.simulationsDict[sim2]["t1new"].tolist()[-1]
                Dt21 = t2- t1
                DU21 = u2 - u1
                if DU21 != 0.0:
                    t1new = t2 + (Dt21)/(DU21) * (self.Ugoal-u2)
                    #Bounding the T1 time
                    #t1new = max((0+0.07/10), min((0.07-0.07/10), t1new))
                    t1new = self.biDirectionalBounding(t1new, 
                                                       self.T1_p_Lbound, 
                                                       self.T1_p_Ubound, 
                                                       self.relDistToBound)
                else:
                    t1new = t2
            
                    
            parsedPrgh["boundaryField"]["Inlet"]["uniformValue"] = self.changeT1(t1new, prghTable)
            parsedPrgh.writeFile()
                
            print("Iteration {} running with the new time set to T1 = {}".format(self.iteration,t1new))

            

            self.runBashCommands(currentCase)



            #Writing all info of the current simulation in to the df_plotting dataFrame
            p_outlet = PatchAverage("p", "Outlet")
            p_inlet = PatchAverage("p", "Inlet")
            U_inlet_mag = PatchMagnitude("U", "Inlet")
            U_inlet_avgmag = PatchAverage("mag(U)", "Inlet")
            #
            df_p_inlet = p_inlet.resultsDataFrame
            df_p_outlet = p_outlet.resultsDataFrame
            df_U_inlet_avgmag = U_inlet_avgmag.resultsDataFrame
            #
            df_plotting = df_p_inlet
            df_plotting["p_in"] = df_plotting["Value"]
            df_plotting = df_plotting.drop(['Value', 'Field', 'ValueType', 'Patch'], axis=1)
            df_plotting["p_in"] = df_p_inlet.iloc[:]["Value"]
            df_plotting["p_out"] = df_p_outlet.iloc[:]["Value"]
            df_plotting["magU_in"] = df_U_inlet_avgmag.iloc[:]["Value"]
            #adding the cavitation number sigma
            df_plotting.iloc[:]["pSat"] = 2337
            df_plotting.iloc[:]["rho"] = 1000
            df_plotting["sigma"] = (df_plotting["p_in"]- df_plotting["pSat"])/(0.5 * df_plotting["rho"] * (df_plotting["magU_in"])**2)

            #adding change in percent of mag_Inlet
            var = list(df_plotting["magU_in"])
            result = list()
            x1 = var[1:]
            x2 = var[:-1]
            for x1, x2 in zip(var[1:], var[:-1]):
                result.append(abs((x1-x2)/x1))
            result = [None] + result
            df_plotting["magU_in_rel"] = result
            var = None
            result = None
            tmpResidual = df_plotting["magU_in_rel"].tolist()[-1]
            if (tmpResidual is not None):
                residual = tmpResidual

            #adding change in percent of mag_Inlet
            var = list(df_plotting["sigma"])
            result = list()
            x1 = var[1:]
            x2 = var[:-1]
            for x1, x2 in zip(var[1:], var[:-1]):
                result.append(abs((x1-x2)/x1))
            result = [None] + result
            df_plotting["sigma_rel"] = result

            #adding the tf1new value to the data frame, for later use durin the extrapolation of the new time step
            df_plotting["t1new"] = t1new

            ###
            U = df_plotting["magU_in"].tolist()[-1]
            residual = abs((self.Ugoal - U)) / self.Ugoal
            df_plotting["residual"] = residual

            #Saving the simulation data into a dictionary for later reuse
            self.simulationsDict[caseName] = df_plotting


            print("Finished iteration {} with a final value of U = {}".format(self.iteration, U))
            

            self.iteration = self.iteration + 1
            
            
            
            
            
if __name__ == "__main__":
    
    studyName = "DebugStudy001"
    studyTemplate = "/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/templates/pythonScript_development_templates/hemisphericalHead_2D_grid8_2_3_totalpmyWave_U5_K0_4_template"
    cwd = "/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/templates/pythonScript_development_templates/"
        
    # For Re = 1.36k, Ugoal=5.245
    Uoptimizer = UInletOptimizer(studyName,
                                cwd,
                                studyTemplate,
                                maxIters=4,
                                Ugoal=5.245,  
                                residual=3,
                                T1_p_Lbound=0.025,
                                T1_p_Ubound=0.09,
                                relDistToBound=0.03)
    
    Uoptimizer.run()
    
