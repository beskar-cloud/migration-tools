# Multi OpenStack cloud backed by same ceph migration use-case

Migration of the OpenStack workload from one cloud to the other when both have connected same ceph is fast and easy to do.

Migration toolset infrastructure:
* cloud administrator node or CI pipeline running [project-migrator.py](./project-migrator.py)
* ceph migrator host accessible via SSH (paramiko) authenticated via SSH keys
* OpenStack domain administrator user in both clouds read as separate OpeStack RC files


Ceph block storage migration is performed from ceph migrator host as typically ceph distributed storage is maintainable from host within cloud infrastructure only.

Migration tool is able to map different server flavors names and also different network names (LUT tables in code atm).


