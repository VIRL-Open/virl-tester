from __future__ import print_function
import sys
import json
import yaml
import os.path


def load_yml(filename, lvl=0):
    if lvl > 10:
        return []
    if type(filename) is file:
        data = yaml.load(filename)
    else:
        with open(filename, 'r') as f:
            data = yaml.load(f)
    if data.get('sims') is None:
        data['sims'] = list()
    for sim in data['sims']:
        sim['topo'] = os.path.expanduser(sim['topo'])
    includes = data.get('includes')
    if includes is not None:
        for include in includes:
            curdir = os.getcwd()
            try:
                path = os.path.dirname(include)
                basename = os.path.basename(include)
                if len(path) > 0:
                    os.chdir(path)
                print("%d:#%s#" % (lvl, path))
                subdata = load_yml(basename, lvl + 1)
            except (IOError, OSError) as e:
                print(e)
            else:
                if subdata is not None:
                    for sim in subdata['sims']:
                        topo = sim['topo']
                        if not os.path.isabs(topo):
                            sim['topo'] = os.path.join(path, topo)
                        sim['source'] = include
                        data['sims'].append(sim)
            os.chdir(curdir)
        del data['includes']
    return data


def main(args):
    print(args)
    with open('test.yml', 'r') as f:
        data = load_yml(f)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    print('yest'+__name__)
    main(sys.argv)
