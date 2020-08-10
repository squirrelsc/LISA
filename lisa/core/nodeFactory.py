from typing import Dict, Optional, cast

from lisa.util import constants

from .node import Node


class NodeFactory:
    @staticmethod
    def createNodeFromConfig(id: str, config: Dict[str, object]) -> Optional[Node]:
        node_type = config.get(constants.TYPE)
        node = None
        if node_type is None:
            raise Exception("type of node shouldn't be None")
        if node_type in [
            constants.ENVIRONMENTS_NODES_LOCAL,
            constants.ENVIRONMENTS_NODES_REMOTE,
        ]:
            is_default = cast(bool, config.get(constants.IS_DEFAULT, False))
            node = Node.createNode(id, node_type=node_type, isDefault=is_default)
            if node.isRemote:
                fields = [
                    constants.ENVIRONMENTS_NODES_REMOTE_ADDRESS,
                    constants.ENVIRONMENTS_NODES_REMOTE_PORT,
                    constants.ENVIRONMENTS_NODES_REMOTE_PUBLIC_ADDRESS,
                    constants.ENVIRONMENTS_NODES_REMOTE_PUBLIC_PORT,
                    constants.ENVIRONMENTS_NODES_REMOTE_USERNAME,
                    constants.ENVIRONMENTS_NODES_REMOTE_PASSWORD,
                    constants.ENVIRONMENTS_NODES_REMOTE_PRIVATEKEYFILE,
                ]
                parameters: Dict[str, str] = dict()
                for key in config:
                    if key in fields:
                        parameters[key] = cast(str, config[key])
                node.setConnectionInfo(**parameters)
        return node

    @staticmethod
    def createNodeFromSpec(
        spec: Dict[str, object], node_type: str = constants.ENVIRONMENTS_NODES_REMOTE
    ) -> Node:
        is_default = cast(bool, spec.get(constants.IS_DEFAULT, False))
        node = Node.createNode(
            "spec", spec=spec, node_type=node_type, isDefault=is_default
        )
        return node