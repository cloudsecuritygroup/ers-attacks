# Attacks on Encrypted Response-Hiding Range Search Schemes in Multiple Dimensions: Experiments

This is the associated artifact for the paper "Attacks on Encrypted Response-Hiding Range Search Schemes in Multiple Dimensions".

**Important:** This repository implements several cryptographic primitives (used for research purposes) which should not be used in production.

## Dependencies 

Our schemes assume prior installation of Python 3.9.0 or above which can be installed from [here](https://www.python.org/downloads/source/).
The `requirements.txt` file in the main directory contains a list of all the necessary dependencies for running our schemes and reproducing our experiments; these dependencies can be installed using the `pip3` command. The dependencies include multiple packages, like numpy, ortools, cryptography and matplotlib.

## Detailed Usage

### The Attacks

This repository contains implementations of the four attacks from our paper:

* **Linear Attack**: This attack works against schemes that construct a multimap mapping each domain point to the set of corresponding records. Concretely, this attack works against the Linear Scheme (Falzon et al. VLDB 2022) and the Naive Scheme (Demertzis et al. SIGMOD 2016).
* **Token Pair Attack**: This attacks successfully reconstructs databases from the leakage of the Rangetree with Universal range cover (Faber et al. ESORICS 2015), Logarithmic-URC (Demertzis et al. SIGMOD 2016), and Range-URC and Quad-BRC (Falzon et al. VLDB 2022). It works by leveraging the fact that all four of these schemes leak the search tokens of neighboring points when a range query of size 2 is issued. In our experiments, we run the attack against our Range-URC scheme. 
* **Range-BRC Attack**: This attack works against the Range-BRC scheme (Falzon et al. VLDB 2022) and leverages token co-occurances. 
* **SRC Attack**: This attack works against non-interactive schemes that use a single range cover (SRC), e.g., Logarithmic-SRC (Demertzis et al. SIGMOD 2016), and the schemes QDAG-SRC, TDAG-SRC, and Quadratic-SRC (Falzon et al. VLDB 2022). The attack works by building an integer linear program whose solution set corresponds to the set of all databases in the reconstruction space. Our implementation simply returns one of the possible solutions. In our experiments, we run the attack against our QDAG-SRC scheme.

### The Datasets

Each of our attacks can be tested on the following three datasets. 

* **Gowalla**: A 4D dataset consisting of $6,442,892$ latitude-longitude points of check-ins 
 from users of the  Gowalla social networking website  between  2009 and 2010.  (https://snap.stanford.edu/data/loc-gowalla.html)
* **Spitz**:  A 2D dataset of $28,837$ latitude-longitude points of phone location data of politician Malte Spitz from Aug 2009 to Feb 2010. (https://crawdad.org/spitz/cellular/20110504)
* **Cali**: A 2D dataset of $21,047$ latitude-longitude points of road network intersections in California. (https://users.cs.utah.edu/~lifeifei/SpatialDataset.htm)

For each of these datasets, we sample the points and generate smaller 2D versions of the originals. These datasets can be found in the `data` directory.

### Execution

* The **Token Pair**, **Range-BRC**, and **SRC** attacks can be run using:
```
python -m attacks.attack [TokPair|RangeBRC|SRC] [path_to_dataset] [path_to_output]
```
where`path_to_output` is a path to where the output of the script should go to and `path_to_dataset` is a path to one of the datasets in `data/`, e.g. 
`
python -m attacks.attack TokPair data/cali-8x8.pickle
`

* Our **Linear** attack requires C++ and is in the folder `linear-attack/`. It requires installation of scons (https://scons.org/) and can be run as follows:

```
scons 
./attack N1 N2 p 
```

where N1 and N2 are the domain side sizes and p is the percentage of responses to the queried (uniformly at random). 

e.g. `./attack 10 10 40`

For most scheme implementations we use: https://github.com/cloudsecuritygroup/ers

In the linear attack we use the PQ-tree implementation: https://github.com/Gregable/pq-trees
