import logging
from typing import Dict, List, Optional, Tuple

from ..constants import DEFAULT_IMAGE
from ..container_daemon_form import ContainerDaemonForm, daemon_to_container
from ..container_types import CephContainer, extract_uid_gid
from ..context import CephadmContext
from ..context_getters import fetch_configs
from ..daemon_form import register as register_daemon_form
from ..daemon_identity import DaemonIdentity
from ..deployment_utils import to_deployment_container

logger = logging.getLogger()


@register_daemon_form
class FcmDedup(ContainerDaemonForm):
    """One fcm-dedup container per OSD on FCM-capable hosts.

    Uses the same Ceph base image as the OSD — a different entrypoint
    argument, not a different image.  /dev is mounted so the process can
    issue NVMe IO passthrough commands via libnvme.
    """

    daemon_type = 'fcm-dedup'
    entrypoint = '/usr/bin/fcm-dedup'

    @classmethod
    def for_daemon_type(cls, daemon_type: str) -> bool:
        return cls.daemon_type == daemon_type

    def __init__(
        self,
        ctx: CephadmContext,
        ident: DaemonIdentity,
        config_json: Dict,
        image: str = DEFAULT_IMAGE,
    ) -> None:
        self.ctx = ctx
        self._identity = ident
        self.image = image

    @classmethod
    def init(
        cls, ctx: CephadmContext, fsid: str, daemon_id: str
    ) -> 'FcmDedup':
        return cls.create(ctx, DaemonIdentity(fsid, cls.daemon_type, daemon_id))

    @classmethod
    def create(
        cls, ctx: CephadmContext, ident: DaemonIdentity
    ) -> 'FcmDedup':
        return cls(ctx, ident, fetch_configs(ctx), ctx.image)

    @property
    def identity(self) -> DaemonIdentity:
        return self._identity

    @property
    def fsid(self) -> str:
        return self._identity.fsid

    @property
    def daemon_id(self) -> str:
        return self._identity.daemon_id

    def customize_container_mounts(
        self, ctx: CephadmContext, mounts: Dict[str, str]
    ) -> None:
        # Required for NVMe IO passthrough via libnvme ioctl.
        mounts['/dev'] = '/dev:rw'

    def customize_container_args(
        self, ctx: CephadmContext, args: List[str]
    ) -> None:
        # --privileged is required for the ioctl path used by libnvme.
        args.append('--privileged')

    def uid_gid(self, ctx: CephadmContext) -> Tuple[int, int]:
        return extract_uid_gid(ctx)

    def get_daemon_args(self) -> List[str]:
        return ['--id', self.daemon_id, '--fsid', self.fsid]

    def create_daemon_dirs(self, data_dir: str, uid: int, gid: int) -> None:
        pass

    def container(self, ctx: CephadmContext) -> CephContainer:
        return daemon_to_container(ctx, self)

    def deploy_daemon_unit(
        self, ctx: CephadmContext
    ) -> None:
        to_deployment_container(ctx, self)
