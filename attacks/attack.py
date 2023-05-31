##
## Copyright 2022 Zachary Espiritu and Evangelia Anna Markatou and
##                Francesca Falzon and Roberto Tamassia and William Schor
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##
import importlib  
import argparse
import pickle

import attacks.tokenpairattack
import attacks.brc_attack
srcortools = importlib.import_module("attacks.src-ortools")





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parameters for attack')
    parser.add_argument('attack_name', choices=['TokPair', 'RangeBRC', 'SRC'])
    parser.add_argument('db_file', nargs='?', default=None)
    parser.add_argument('output_file_path', nargs='?', default='output.csv')
    args = parser.parse_args()

    print("Loading database...")
    db = None
    if args.db_file:
        with open(args.db_file, "rb") as fp:
            db = pickle.load(fp)

    print("Attacking...")

    if args.attack_name == "TokPair":
        attacks.tokenpairattack.attack(args.attack_name, db, args.output_file_path)
    elif args.attack_name == "RangeBRC":
        attacks.brc_attack.attack(args.attack_name, db, args.output_file_path)
    elif args.attack_name == "SRC":
        srcortools.attack(args.output_file_path, db)

    else:
        print("I don't know this attack")
