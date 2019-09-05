#!/usr/bin/env python2.7
# play with, test using ConfigParser to find config files
import sklearnHelperLib as skhelper
import ConfigParser

if False:	# this code has been moved to skhelper.getConfig()
    cp = ConfigParser.ConfigParser()
    cp.optionxform = str # make keys case sensitive

    # generate a path up multiple parent directories to search for config file
    # (up to 6 levels above)
    cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,6)]]
    cl.reverse()    # Note: later files in the list override earlier files.

    cp.read(cl + fileList)

cp = skhelper.getConfig()

print cp.sections()

print cp.items('CLASS_NAMES')

