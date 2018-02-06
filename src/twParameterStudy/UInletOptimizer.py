
from PatchPostProcessing import PatchAverage, PatchMagnitude
from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParameterFile import ParameterFile
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

#goal : 5.245 U inlet -> Re = 1.35e5
    #0.0254 m
    #9.7937E-7 m^2 / s


    def __init__(self):
        self.studyName = "hemisphHead_grid8_2_3_U1_36k_K0_4_U5_25_study001"
        self.studyTemplate = "/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/templates/pythonScript_development_templates/hemisphericalHead_2D_grid8_2_3_totalpmyWave_U5_K0_4_template"
        self.cwd = "/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/templates/pythonScript_development_templates/"
        
        os.chdir(self.cwd)
        os.mkdir(self.studyName)
        self.studyWorkingDirectory = self.cwd + self.studyName

        self.sol = SolutionDirectory(self.studyTemplate)
        self.iteration = 0
        self.maxIter = 10

        self.t1new = None
        self.newPrghTable = list()
        self.newDeltaPDomain = 25
        self.targetSigma = 0.8

        self.p_outlet = None
        self.p_inlet = None
        self.U_inlet_mag = None
        self.U_inlet_avgmag = None

        # For Re = 1.36k
        self.Ugoal = 5.245

        self.simulationsDict = dict()
        self.residual = 3


    def setInitialValues(self, case):
        U = Vector(0,0,0)
        p = 2500000
        prgh = 2500000
   
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
    

    def changeTimes(self, deltaT, tStart, table):
        table = table[1]
        for i in range(len(table)):
            if table[i][0] > tStart:
                table[i][0] = table[i][0] + deltaT
        return table

    def changeValues(self, value, value_n, table):
        table = table[1]
        for i in range(len(table)):
            if table[i][1] == value:
                table[i][1] = value_n
        return table

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
    
    
    def boundingT1(self, t1new, bound_l, bound_u, relDistToBounds):
        relD = relDistToBounds
        # The new T1 value cannot be equal to his bounding values. 
        # Doing so, yields a non-valid table for the BC in question
        return max((bound_l+bound_u*relD), min((bound_u-bound_u*relD), t1new))

        
    def run(self):
        print("Running main loop for a maximum of {} iterations".format(self.maxIter))
        while (self.iteration < self.maxIter and self.residual > 0.001): #The residual calculation doesnt mean shit yet. 
            # Leave it out to avoid unexpected bahaviour
            os.chdir(self.studyWorkingDirectory)
            caseName = "sim" + str(self.iteration)

            #Cloning the template case
            cloneCasePath = os.path.join(self.studyWorkingDirectory, caseName)
            currentCase = self.sol.cloneCase(cloneCasePath)
            shutil.copyfile(self.studyTemplate + "/run", cloneCasePath + "/run")
            os.chdir(currentCase.name)

            #parsing the prgh file
            parsedPrgh = os.path.join(currentCase.name, "0.000000/p_rgh")
            parsedPrgh = ParsedParameterFile(parsedPrgh)
            prghTable = parsedPrgh["boundaryField"]["Inlet"]["uniformValue"]

            #The bound of T1. For prototyping, they are set manually
            t1Bound_l = 0.0
            t1Bound_u = 0.21

            #first simulation
            if self.iteration == 0:
                self.setInitialValues(currentCase)
                t1new = self.getT1Value(prghTable)
            #second simulation
            elif self.iteration == 1:
                sim0 = "sim" + str(0)
                Ulist0 = self.simulationsDict[sim0]["magU_in"].tolist()
                u1 = Ulist0[-1]
                u2 = self.Ugoal
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
                    #Bounding the T1 time
                    #t1new = max((0+0.07/10), min((0.07-0.07/10), t1new))
                    t1new = self.boundingT1(t1new, t1Bound_l, t1Bound_u, 0.03)
                else:
                    t1new = t2
                parsedPrgh["boundaryField"]["Inlet"]["uniformValue"] = self.changeT1(t1new, prghTable)
                parsedPrgh.writeFile()
            #all following simulations
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
                    t1new = self.boundingT1(t1new, t1Bound_l, t1Bound_u, 0.03)
                else:
                    t1new = t2
                parsedPrgh["boundaryField"]["Inlet"]["uniformValue"] = self.changeT1(t1new, prghTable)
                parsedPrgh.writeFile()
                
            print("Iteration {} running with the new time set to T1 = {}".format(self.iteration,t1new))

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
    Uoptimizer = UInletOptimizer()
    Uoptimizer.run()
    