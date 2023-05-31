//
// Copyright 2022 Zachary Espiritu and Evangelia Anna Markatou and
//                Francesca Falzon and Roberto Tamassia and William Schor
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

#include <assert.h>
#include <iostream>
#include <stdlib.h>
#include <set>
#include <string>
#include <map>
#include "pqnode.h"
#include "pqtree.h"
#include <cstdlib>
#include <fstream>
#include <string> 

#include <chrono>
using namespace std::chrono;
using namespace std;

typedef vector<pair<int,int> > tuple_list;


bool isPrime(int n) {
    if (n < 1) {
        return false;
      }

    if (n == 1) {
        return true;
      }
      
    if (n == 2) {
        return true;
      }
  
    for (int i = 2; i < n; i++) {
        if (n % i == 0) {
            return false;
          }
        }
    return true;
}

set<int> getSetTokensFromResponses(set<vector<int> >  responses) {
  set<int> tokens;
  for (set<vector<int> >::iterator tokenset = responses.begin(); tokenset != responses.end(); ++tokenset) {
    for(int i=0; i < (*tokenset).size(); i++){
      tokens.insert((*tokenset)[i]);
    }
  }
  return tokens;



}

vector< set<vector<int> > > Get1DSlices(set<vector<int> >  responses) {
  vector< set<vector<int> > > slices;
  
  // For each tokenset in the responses 
  for (set<vector<int> >::iterator tokenset = responses.begin(); tokenset != responses.end(); ++tokenset) {
    set<vector<int> > combine;
    vector<set<vector<int> > > toRemove;
    combine.insert(*tokenset);
    set<int> tokens = getSetTokensFromResponses(combine);

    // For each slice we have created
    for (vector< set<vector<int> > >::iterator slice = slices.begin(); slice != slices.end(); ++slice) {
      //  Get the set of tokens in this slice
      set<int> sliceTokens = getSetTokensFromResponses(*slice);

      // Find the intersection of the slice tokens with the tokenset tokens
      vector<int> intersection;

      set_intersection(tokens.begin(), tokens.end(),
                          sliceTokens.begin(), sliceTokens.end(),
                          back_inserter(intersection));

      // If the intersection has more than 2 elements, combine this slice with the tokenset
      if (intersection.size() >= 2) {
        for (set<vector<int> >::iterator sliceTokenset = (*slice).begin(); sliceTokenset != (*slice).end(); ++sliceTokenset) {
          combine.insert((*sliceTokenset));
        }
        toRemove.push_back((*slice));
      }    
    }
    // Once we have added all possible slices to combine, insert it in slices and remove them from slices.
    for (vector< set<vector<int> > >::iterator removeSlice = toRemove.begin(); removeSlice != toRemove.end(); ++removeSlice){
      slices.erase(remove(slices.begin(), slices.end(), (*removeSlice)), slices.end());
    }
    slices.push_back(combine);
    combine.clear();
  }
  return slices;
}

set<vector< tuple<int, int, int> > > Get3DResponses(int N0, int N1, int N2, vector<tuple<int, int, int>  > points) {
  set<vector< tuple<int, int, int> > >  responses;

  for (int min0 = 1; min0 < N0; min0++) {
    for (int min1 = 1; min1 < N1; min1++) {
      for (int min2 = 1; min2 < N2; min2++) {
        for (int max0 = min0; max0 < N0; max0++) {
          for (int max1 = min1; max1 < N1; max1++) {
            for (int max2 = min2; max2 < N2; max2++) {
              vector<tuple<int, int, int> > r;
              for(int i=0; i < points.size(); i++){
                if (get<0>(points[i])<= max0 && get<0>(points[i])>= min0 && get<1>(points[i])<= max1 && get<1>(points[i])>= min1 && get<2>(points[i])<= max2 && get<2>(points[i])>= min2) {
                  r.push_back( points[i] );
                }
              }
              if (isPrime(r.size() )){
                responses.insert(r);
              }
            }
          }
        }
      }
    }
  }
return responses;
}



string ReadableType(PQNode::PQNode_types type) {
  if (type == PQNode::leaf) {
    return "leaf";
  } else if (type == PQNode::pnode) {
    return "P-Node";
  } else if (type == PQNode::qnode) {
    return "Q-Node";
  }
  return "unknown";
}

void ReduceBy(const set<int>& reduce_set, PQTree* tree) {
  tree->SafeReduce(reduce_set);
}


vector<tuple<int, int, int> > makeSearchTokens3D(int N0, int N1, int N2) {
  vector<tuple<int, int, int> >  tl;
  for(int x=0; x < N0; x++){
    for(int y=0; y < N1; y++){
      for(int z=0; z < N2; z++){
        tl.push_back(make_tuple(x,y,z));
      }
    }
  }
  return tl;
}




map<tuple<int, int, int>, int> getPairToLabelsMap3D(vector<tuple<int, int, int> > points) {
  set<int> used;
  map<tuple<int, int, int>, int>  mp;
  for(vector<tuple<int, int, int> >::iterator point = points.begin(); point != points.end(); ++point) {
    int newRand = rand() %100000;
    while (used.find(newRand) != used.end()) {
      newRand = rand() %100000;
    }
    used.insert(newRand);
    mp[(*point)]=newRand; 
  }
  return mp;
}


set<vector<int> >  replaceWithTokens3D(map<tuple<int, int, int>, int> labelMap, set<vector< tuple<int, int, int> > > responses) {
  set<vector<int> > newResponses;

  for (set<vector< tuple<int, int, int> > >::iterator tokenset = responses.begin(); tokenset != responses.end(); ++tokenset) {
    vector<int>  newTokenset;
    for(int i=0; i < (*tokenset).size(); i++){
      newTokenset.push_back(labelMap[(*tokenset)[i]]);
    }
    newResponses.insert(newTokenset);
  }
  return newResponses;
}


set<int> getAllTokens(set<vector<int> >  newSlice) {
  set<int> tokens;
    for ( set<vector<int> >::iterator tokenset = newSlice.begin(); tokenset !=  newSlice.end(); ++tokenset) {
      for(int i=0; i < (*tokenset).size(); i++){
        tokens.insert((*tokenset)[i]);
      }
    }

  return tokens;
}



vector<list<int> >  orderSlices(vector< set<vector<int> > > newSlices) {
  vector<list<int> >  orderedSlices;

  for (vector< set<vector<int> > >::iterator slice = newSlices.begin(); slice != newSlices.end(); ++slice) {
    set<int> tokens = getAllTokens((*slice));
    PQTree tree(tokens);

    for ( set<vector<int> >::iterator tokenset = (*slice).begin(); tokenset !=  (*slice).end(); ++tokenset) {

      // Make vector into set
      set<int> setTokenSet; 
      for(int i=0; i < (*tokenset).size(); i++){
        setTokenSet.insert((*tokenset)[i]);
      }
      ReduceBy(setTokenSet, &tree);
    }
    orderedSlices.push_back(tree.Frontier());
  }
  return orderedSlices;
}


vector<list<tuple<int, int, int> > > returnSlicesToST3D(vector<list<int> > orderedSlices, map<int,tuple<int, int, int> > labelMap) {
  vector<list<tuple<int, int, int> > > newOrderedSlices;

  for (vector<list<int> >::iterator slice = orderedSlices.begin(); slice != orderedSlices.end(); ++slice) {
    if ((*slice).size() >= 2) {
      list<tuple<int, int, int> > pairSlice;

      for (list<int>::iterator point = (*slice).begin(); point != (*slice).end(); ++point) {
        pairSlice.push_back(labelMap[(*point)]);
      }


      newOrderedSlices.push_back(pairSlice);
    }
  }
  return newOrderedSlices;
}






map<int, tuple<int, int, int> > getLabelsToPairMap3D(map<tuple<int, int, int>, int> mp) {
  map<int, tuple<int, int, int> >  mp2;
  for(map<tuple<int, int, int>, int> ::iterator iter = mp.begin(); iter != mp.end(); ++iter) {
    mp2[iter->second]= iter->first;
  }
  return mp2;
}


vector<list<tuple<int, int, int> > > getCorrectOrders3D(int N0, int N1, int N2) {

  vector<list<tuple<int, int, int> > > newOrderedSlices;

  if (N2 > 2) {
    for (int x = 1; x < N0; x++) {
      for (int y = 1; y < N1; y++) {
        list<tuple<int, int, int> > row;
        for (int z = 1; z < N2; z++) {
          row.push_back(make_tuple(x,y,z));
        }
        newOrderedSlices.push_back(row);
      }
    }
  }
  
  if (N1 > 2) {
    for (int x = 1; x < N0; x++) {
      for (int z = 1; z < N2; z++) {
        list<tuple<int, int, int> > row;
        for (int y = 1; y < N1; y++) {
          row.push_back(make_tuple(x,y,z));
        }
      newOrderedSlices.push_back(row);
      }
    }
  }

  
  if (N0 > 2) {
    for (int y = 1; y < N1; y++) {
      for (int z = 1; z < N2; z++) {
        list<tuple<int, int, int> > row;
        for (int x = 1; x < N0; x++) {
          row.push_back(make_tuple(x,y,z));
        }
      newOrderedSlices.push_back(row);
      }
    }
  }

  return newOrderedSlices;
}



bool checkCorrect3D(int N0, int N1, int N2, vector<list<tuple<int, int, int> > > OrderedSlices) {
  vector<list<tuple<int, int, int> > > correctOrderedSlices = getCorrectOrders3D(N0,N1,N2);

  if (correctOrderedSlices.size() != OrderedSlices.size() ) {
    cout << "wrong order\n";
    return false;
  }

  for (vector<list<tuple<int, int, int> > >::iterator slice = OrderedSlices.begin(); slice != OrderedSlices.end(); ++slice) {
    bool inCorrect = false;
    for (vector<list<tuple<int, int, int> > >::iterator good_slice = correctOrderedSlices.begin(); good_slice != correctOrderedSlices.end(); ++good_slice) {
      if ((*slice) == (*good_slice)) {
        inCorrect = true;
      }
      reverse((*good_slice).begin(),(*good_slice).end());
      if ((*slice) == (*good_slice)) {
        inCorrect = true;
      }  
      reverse((*good_slice).begin(),(*good_slice).end());    

    }
    if (inCorrect == false) {
      return false;
    }
  }
  return true;
}



float checkAccuracy3D(int N0, int N1, int N2, vector<list<tuple<int, int, int> > > OrderedSlices) {
  int correctEdges=0;
  int totalEdges=0;


  for (vector<list<tuple<int, int, int> > >::iterator slice = OrderedSlices.begin(); slice != OrderedSlices.end(); ++slice) {
    for(int i=1; i < (*slice).size(); i++){
      auto first = (*slice).begin();
      auto second = (*slice).begin();
      advance(first, i-1);
      advance(second, i);

      tuple<int, int, int> p0 = *first;
      tuple<int, int, int> p1 = *second;

      int p00 = get<0>(p0);
      int p01 = get<1>(p0);
      int p02 = get<2>(p0);
      int p10 = get<0>(p1);
      int p11 = get<1>(p1);
      int p12 = get<2>(p1);
      totalEdges++;

      
      if ( p00 == p10 && p01== p11 && ((p02 == p12-1) || (p02 == p12+1) )) {
        correctEdges++;
      } else if ( p00 == p10 && p02== p12 && ((p01 == p11-1) || (p01 == p11+1) )) {
        correctEdges++;
      } else if ( p01 == p11 && p00== p10 && ((p02 == p12-1) || (p02 == p12+1) )) {
        correctEdges++;
      } else if ( p01 == p11 && p02== p12 && ((p00 == p10-1) || (p00 == p10+1) )) {
        correctEdges++;
      } else if ( p02 == p12 && p00== p10 && ((p01 == p11-1) || (p01 == p11+1) )) {
        correctEdges++;
      } else if ( p02 == p12 && p01== p11 && ((p00 == p10-1) || (p00 == p10+1) )) {
        correctEdges++;
      } 

    }
  }

  return (float)correctEdges/(float)totalEdges;
}

set<vector< tuple<int, int, int> > > trim3DResponses(set<vector< tuple<int, int, int> > > responses, int p) {
  set<vector< tuple<int, int, int> > > trimResponses;
  for (set<vector< tuple<int, int, int> > >::iterator resp = responses.begin(); resp != responses.end(); ++resp) {
    int randNum;
    randNum = rand() % 100;
    if (randNum < p) {
      trimResponses.insert((*resp));
    }
  }
  return trimResponses;
}



int main(int argc, char **argv) {
    // TO run : ./attack N0 N1 p
  // Eg. ./attack 10 10 100 
  int N0 = atoi(argv[1])+1;
  int N1 = atoi(argv[2])+1;
  int N2 = 2;
  int p = atoi(argv[3]);

  if (N0 <= 0) {

    cout << "Invalid N0 " << N0;
    return 0;
  }
  if (N1 <= 0) {
    cout << "Invalid N1" << N1;
    return 0;
  }
  if (N2 <= 0) {
    cout << "Invalid N2" << N1;
    return 0;
  }

  if (p < 0 || p >100) {
    cout << "Invalid p" << p;
    return 0;
  }


  cout << "Generate responses " <<  endl;

  vector<tuple<int, int, int> > points =  makeSearchTokens3D(N0,N1,N2);
  set<vector< tuple<int, int, int> > > responses = trim3DResponses(Get3DResponses(N0,N1, N2,points), p);
  map<tuple<int, int, int>, int> labelMap = getPairToLabelsMap3D(points);
  map<int, tuple<int, int, int> > labelMap2 = getLabelsToPairMap3D(labelMap);
  set<vector<int> > newResponses = replaceWithTokens3D(labelMap,responses);

  // Attack starts
  auto start = high_resolution_clock::now();
  cout << "Get1DSlices " <<  endl;
  vector< set<vector<int> > > slices = Get1DSlices(newResponses);

  cout << "PQ-tree time " <<  endl;
  vector<list<int> > OrderedSlices = orderSlices(slices);

  // Attack ends

  vector<list<tuple<int, int, int> > >  OrderedTokens = returnSlicesToST3D(OrderedSlices,labelMap2);
  bool correct = checkCorrect3D(N0, N1, N2, OrderedTokens);
  float accuracy = checkAccuracy3D(N0, N1, N2, OrderedTokens);


  auto stop = high_resolution_clock::now();

  auto duration = duration_cast<seconds>(stop - start);
  int UID = rand() % 1000000;
  
  cout << "Are we correct? " << correct<< endl;
  cout << "Are we accurate? " << accuracy<< endl;
  cout << "Attack finished in " << duration.count() << " seconds." <<endl;

  return correct;
}
