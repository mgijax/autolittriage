# play with, test using configparser to find config files
import utilsLib
import configparser

cp = utilsLib.getConfig() # the logic to search up directories in in utilsLib

print(cp.sections())

print(cp.items('CLASS_NAMES'))

