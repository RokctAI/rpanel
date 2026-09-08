# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

from abc import ABC, abstractmethod


class VPSProvider(ABC):
    """
    Abstract Base Class defining the contract for all VPS Cloud Providers
    (e.g., OVH, Hetzner, DigitalOcean, AWS) managed natively by rpanel.
    """

    @abstractmethod
    def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
        """
        Orders and provisions a brand new VPS instance dynamically.

        Returns:
                dict: Standardized metadata including status, order_id, invoice_id, and provision URL.
        """
        pass

    @abstractmethod
    def rebuild_vps(
        self, vps_id: str, image_name: str, ssh_keys: list, **kwargs
    ) -> bool:
        """
        Re-installs/rebuilds a clean OS image on an existing VPS instance.

        Returns:
                bool: True if execution succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def get_vps_status(self, vps_id: str) -> dict:
        """
        Retrieves runtime state, resource specifications, and billing info.

        Returns:
                dict: Standardized status dictionary (vps_id, state, ip, memory, vcpus, raw_info).
        """
        pass

    @abstractmethod
    def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
        """
        Triggers a reboot action on the VPS instance.

        Returns:
                bool: True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def terminate_vps(self, vps_id: str, **kwargs) -> bool:
        """
        Permanently cancels and terminates the VPS instance subscription.

        Returns:
                bool: True if successful, False otherwise.
        """
        pass
