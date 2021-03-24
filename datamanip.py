import pandas as pd
import requests
from tqdm import tqdm
import math

class dataCleaner:
    """
    dataCleaner provides methods to read data files using given
    instructions, to query SIMBAD using the data files, and to
    export a modified data file with information that is 
    required for the frontend.
    """
    def __init__(self):
        """
        Initialise data cleaner
        """
        self.hasInfo = []
        print("Cleaner initialised.")
        print("Proceed to add files using initInput command.")

    def addByteInfo(self, path:str, lines:list, byteC:list, labelC:list):
        """
        Add information about the line and column location
        of byte description of the data file.

        path    - path to the readme file
        lines   - start and end lines (list)
        byteC   - byte start and end columns (list)
        labelC  - label start and end columns (list)
        """
        self.readme = path
        self.readmeLines = lines
        self.readmeBytes = byteC
        self.readmeLabel = labelC
        self.hasInfo.append(True)

    def addFiles(self, lPath:str, hPath:str, obsCat:str, bibCat:str):
        """
        Add path to source data files.

        lPath   - path to the lmxb catalog
        hPath   - path to the hmxb catalog
        obsCat  - astrosat observation catalog
        bibCat  - astrosat publication catalog
        """
        self.lPath = lPath
        self.hPath = hPath
        self.obsCat = obsCat
        self.bibCat = bibCat
        self.hasInfo.append(True)

    def inputInterface(self,
                  readme:list, lines:list, byteC:list, labelC:list,
                  lPath:str, hPath:str, obsCat:str, bibCat:str):
        """
        Interface for inputting data.

        readme  - path to README file
        lines   - start and end lines in README
        byteC   - byte start and end columns
        labelC  - label start and end columns
        lPath   - path to the lmxb catalog
        hPath   - path to the hmxb catalog
        obsCat  - astrosat observation catalog
        bibCat  - astrosat publication catalog
        """
        self.addByteInfo(readme, lines, byteC, labelC)
        self.addFiles(lPath, hPath, obsCat, bibCat)
        print("Source data informations added.")

    @staticmethod
    def raiseMissingInfoError():
        print("Please call inputInterface beforehand.")

    def __byteIndexDict(self, path:str, lines:list, byteC:list, labelC:list):
        """
        Reads the README file for the byte-to-byte description of the
        dat files and makes a dictionary of data labels and their indices.
        To be used inside a function to retrieve data from dat file and
        make a DataFrame object out of it.
        
        path - path to the README file
        lines - list containing starting and ending index of relevant lines
        byteC - column number of the byte indices
        labelC - column number of the label
        """
        if self.hasInfo[0] and self.hasInfo[1]:
            with open(path,"r") as f: 
                def isValid(line):
                    return (line[byteC[0]:byteC[1]]!=7*" " and
                            line[labelC[0]:labelC[1]]!=3*"-")
                descLines = f.readlines()[lines[0]:lines[1]]
                byteIndex = [[int(byt) for byt in 
                              line[byteC[0]:byteC[1]].split("-")] 
                             for line in descLines if isValid(line)]
                dataLabel = [line[labelC[0]:labelC[1]].strip() 
                             for line in descLines if isValid(line)]
                byteDict = {}
                for _ in range(len(byteIndex)):
                    byteDict[dataLabel[_]]=byteIndex[_]
                self.byteDict = byteDict
                print("Byte dictionary generated.")
        else:
            dataCleaner.raiseMissingInfoError()

    def makeCatalog(self):
        """
        Generates the catalog of lmxb and hmxb data.

        Please run initInfo before running this command.
        """
        self.__byteIndexDict(self.readme, self.readmeLines,
                             self.readmeBytes, self.readmeLabel)

        def _makeCat(path:str, byte:dict) -> pd.DataFrame:
            with open(path,'r') as f:
                dArray = []
                for line in f.readlines():
                    line = line[:-2]
                    data = []
                    for label in list(byte):
                        index = byte[label]
                        if len(index)==1:
                            index*=2
                        data.append(line[index[0]-1:index[1]].strip())
                    dArray.append(data)
                df = pd.DataFrame(data=dArray, columns=list(byte))
                return df

        self.lmxb = _makeCat(self.lPath, self.byteDict)
        self.hmxb = _makeCat(self.hPath, self.byteDict)
        self.catalog = pd.concat([self.lmxb, self.hmxb])
        print("Catalog imported successfully.")

    def __coordsQuery(self, n:int, rad:float) -> str:
        """
        Transient function used inside coordinatesQuery
        for finer control of the query.

        n   - index of the datapoint to query about
        rad - radius of the SIMBAD query
        """
        line = self.catalog.iloc[n]
        PREFIX = r"http://simbad.u-strasbg.fr/simbad/sim-coo?"
        FORMAT = r"output.format=ASCII&"
        COORDS = r"Coord={}%20{}%20{}%20{}{}%20{}%20{}&Radius={}".format(
            line["RAh"],line["RAm"],line["RAs"],
            line["DE-"],line["DEd"],line["DEm"],line["DEs"],rad)
        query = requests.get(PREFIX+FORMAT+COORDS)
        return query.text

    @staticmethod
    def __idQuery(identf: str) -> str:
        """
        Transient function used inside coordinatesQuery
        for querying using identifiers

        id  - identifier of the object
        """
        PREFIX = r"http://simbad.u-strasbg.fr/simbad/sim-id?"
        FORMAT = r"output.format=ASCII&Ident="
        query = requests.get(PREFIX+FORMAT+identf)
        return query.text

    def coordinatesQuery(self, n:int, flag) -> str:
        """
        This function queries SIMBAD for data at n-th row of the catalog
        by choosing a suitable radius of query so as to obtain a single
        result.

        n       - index of data to query
        flag    - (b) for debugging purpose to list radius during iterations
        """
        RAD = 0.01
        STEP = 0.001
        query = self.__coordsQuery(n, RAD)
        count = [0,0]
        factor = 0
        shdLoop = True
        while(shdLoop):
            if query[0]=="!":
                count[0]+=1
                if count[0] > 3:
                    factor = count[0]**2
                else:
                    factor = 1
            elif query.split("\n\n")[2][0]=="N":
                count[1]+=1
                if count[1] > 3:
                    factor = -count[1]**2
                else:
                    factor = -1
            else:
                shdLoop = False
                continue
            if count[1] > 15 and factor < 0:
                identifier = query.split("\n\n")[3].split(
                    "\n")[2].split("|")[2].strip()
                query = dataCleaner.__idQuery(identifier)
                break
            RAD += STEP*factor
            if RAD < 0:
                RAD *= STEP
            if flag:
                print(RAD)
            query = self.__coordsQuery(n, RAD)
        return query

    def getQueryInfo(self, n:int):
        """
        Retrives the list of identifiers and bibcodes for n-th
        datapoint in the catalog.

        n   - the object of interest
        """
        def __getInfo(name:str, amt:int, length:int) -> list:
            info = []
            for fields in self.coordinatesQuery(n, 0).split("\n\n"):
                if fields[:len(name)]==name:
                    lines = fields.split("\n")
                    for j in lines[1:]:
                        for k in range(amt):
                            info.append(j[k*length:(k+1)*length].strip())
            return [i for i in info if i!=""]
        identifiers = __getInfo("Identifiers", 3, 32)
        bibcodes = __getInfo("Bibcodes", 4, 21)
        return {"identifiers":identifiers,
                "bibcodes":bibcodes}

    def makeObsCatalog(self):
        """
        Creates a DataFrame object of the astrosat
        catalog of observation.
        """
        ObsArray = []
        with open(self.obsCat,'r') as f:
            for line in f.read().strip().split("\n"):
                datas = line.strip().split("\t")
                datas = datas[1:6]+datas[6].split(":: ")+datas[7:]
                if datas[-1] == None:
                    datas.insert(5, "")
                    del datas[-1]
                ObsArray.append([i.strip() for i in datas])
        self.ObsCatalog = pd.DataFrame(data=ObsArray)
        print("Observation catalog imported successfully.")
    
    def makeBibCatalog(self):
        """
        Creates a DataFrame object of the astrosat
        publication catalog.
        """
        BibArray = []
        with open(self.bibCat, 'r', encoding='utf-8') as f:
            LABELS = ["title", "authors", "bibcode", "url"]
            file = f.read().strip()
            papers = file.split("\n\n\n")
            for paper in papers:
                fields = paper.split("\n")
                fields = fields[:3]+[fields[-1]]
                fields[0] = fields[0].strip()[7:].strip()
                fields[1] = fields[1].strip()[9:].strip()
                fields[2] = fields[2].strip().replace(
                    "Bibliographic Code:","").strip()
                fields[3] = fields[3].strip().replace(
                    "URL: <a href=\"","")[:-26].strip()
                BibArray.append(fields)
            self.BibCatalog = pd.DataFrame(data=BibArray, columns=LABELS)
            print("Publication catalog imported successfully.")

    def filterCatalog(self, n:int) -> dict:
        """
        Used to check if the object of interest is observed by Astrosat,
        and whether if any paper in the publication catalog has referred
        to the data.

        n   - data point of interest
        """
        query = self.getQueryInfo(n)
        isObserved = False
        isReferred = False
        references = []
        identifiers = []
        for identifier in query["identifiers"]:
            if identifier in list(self.ObsCatalog[6]):
                isObserved = True
                identifiers.append(identifier)
        for bibcode in query["bibcodes"]:
            if bibcode in list(self.BibCatalog["bibcode"]):
                isReferred = True
                references.append(bibcode)
        return {"isObserved":isObserved,
                "isReferred":isReferred,
                "identifiers":identifiers,
                "references":references}

    @staticmethod
    def __CelestialToGeo(data: pd.DataFrame) -> dict:
        """
        Converts Right-Ascension and Decliation values
        to Latitude and Longitude.

        data    - single datapoint from a DataFrame object
        """
        lng = ((float(data["RAh"])*15) +
               (float(data["RAm"])*0.25) +
               (float(data["RAs"])*0.004166))
        lat = ((float(data["DEd"])) +
               (float(data["DEm"])/60) +
               (float(data["DEs"])/3600))*float(data["DE-"]+data["DEd"])
        return {"latitude":lat,
                "longitude":lng}

    def combCatalog(self):
        """
        Creates a new DataFrame object containing information
        about as to whether the data are referred in any publication
        or if it has been observed by astrosat, and if it is referred,
        the list of bibcodes of papers referring the data.
        """
        observed = []
        referred = []
        references = []
        identifiers = []
        latitude = []
        longitude = []
        for _ in tqdm(range(len(self.catalog))):
            line = self.catalog.iloc(_)
            geoCoord = DataCleaner.__CelestialToGeo(line)
            latitude.append(geoCoord["latitude"])
            longitude.append(geoCoord["longitude"])
            dataFilter = self.filterCatalog(_)
            observed.append(dataFilter["isObserved"])
            referred.append(dataFilter["isReferred"])
            references.append(dataFilter["references"])
            identifiers.append(dataFilter["identifiers"])
        self.newCatalog = self.catalog
        self.newCatalog["lat"] = latitude
        self.newCatalog["lng"] = longitude
        self.newCatalog["isObserved"] = observed
        self.newCatalog["isReferred"] = referred
        self.newCatalog["references"] = references
        self.newCatalog["identifiers"] = identifiers
        print("New catalog has been generated succesfully.")

    def exportNewCatalog(self, path:str):
        """
        Exports the new catalog in csv format to the given path.

        path    - location to save the file
        """
        self.newCatalog.to_json(path, index=True, orient="records")
        print("New catalog has been successfully exported.")
