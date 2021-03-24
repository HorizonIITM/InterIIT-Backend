# import the dataCleaner class
from datamanip import dataCleaner
import time

# initialise cleaner object
run = dataCleaner()

# add input datas
run.inputInterface(
    r"./data/ReadMe",
    [64,130],
    [1,8],
    [23,32],
    r"./data/lmxbcat.dat",
    r"./data/hmxbcat.dat",
    r"./data/AS_observations_cat_Sept2018.txt",
    r"./data/AS_publications2019-21.txt"
)

# create dataframes
run.makeCatalog()
run.makeObsCatalog()
run.makeBibCatalog()

# create new catalog used in the frontend
run.combCatalog()

# export to CSV
start = time.time()
run.exportNewCatalog(r"./data/output.json")
print("Execution time: ",round(time.time()-start,3)," s")