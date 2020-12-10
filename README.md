# LFM--Online-Appendix
You can find here the code for the article ["Design of a Continuous Local Flexibility Market with Network Constraints"](http://arxiv.org/abs/2012.00505).

## Case files
The csv files contain the network data and are gathered in a Python script:
 * **baseMVA.csv, branch.csv, bus.csv, gen.csv, gencost.csv, PTDF.csv**: Network data.
 * **Case.py**: Builds the case file from the different csv files.
 * **requests.csv**: Flexibility requests.
 * **offers.csv**: Flexibility offers.

## Run the market clearing algorithm
The script **Market_clearing.py** should be run to simulate the matching of the requests in **requests.csv** and the offers **offers.csv** in by the continuous market.

## Grid contraints
Grid constraints are checked by the function implemented in **PTDF_check.py**, which is called by **Market_clearing.py**
