from typing import Dict
import os
import json

class ClusterConfigException(Exception):
    pass

def read_job_cluster_config(path_to_config: str, cluster_type: str = None) -> Dict:
    cluster_config = dict()

    if os.path.exists(path_to_config):
        with open(path_to_config, "r") as f:
            config = json.load(f)

            base_config = config.get('base_config', None)
            if base_config:
                if "cluster_configs" in config:
                    if cluster_type in config["cluster_configs"]:
                        base_config.update(config["cluster_configs"][cluster_type])
                    else:
                        ClusterConfigException(f"Cluster type {cluster_type} is not found")
                cluster_config = base_config
            else:
                raise ClusterConfigException(f"Base config section is not found in file {path_to_config}")
    else:
        raise ClusterConfigException(f"Cluster config by path {path_to_config} is not found")

    return cluster_config