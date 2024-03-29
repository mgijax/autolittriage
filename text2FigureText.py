# Read a text file (extracted text) (from stdin) and run the
#  figure text extraction, output the figure text to stdout.
#

import sys
import argparse
import figureText

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Read text from stdin, write figure text to stdout.')

    parser.add_argument('--figoption', dest='figOption', action='store',
        choices=['legends', 'legParagraphs', 'legCloseWords'],
        default='legCloseWords',
        help="the type of fig text extraction. See figureText.py. " +
        "legCloseWords is default. This is used by littriageload.")

    parser.add_argument('--numwords', '--words', dest='numWords',action='store',
        type=int, default=50,
        help="number of words for legCloseWords figoption. See figureText.py." +
        " Default: 50 (used by littriageload)")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()
    args.inputFile = sys.stdin	# set here in case we ever have input file opt

    return args
#---------------------------

args = parseCmdLine()

def main():
    converter = figureText.Text2FigConverter(conversionType=args.figOption,
                                                numWords=args.numWords)
    text = args.inputFile.read()
    for ft in converter.text2FigText(text):
        print('---------------')
        print(ft)
    print('-------------')

if __name__ == "__main__":
    main()
