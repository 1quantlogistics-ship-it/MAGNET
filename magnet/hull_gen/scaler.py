"""
hull_gen/scaler.py - Parametric hull scaling and transformation.

ALPHA OWNS THIS FILE.

Module 16 v1.0 - Parametric Hull Definition.
"""

from typing import Optional
import copy

from .parameters import HullDefinition


class HullScaler:
    """Scale and transform parent hulls to meet requirements."""

    @staticmethod
    def scale_to_lwl(
        parent: HullDefinition,
        target_lwl: float,
    ) -> HullDefinition:
        """
        Scale hull to target waterline length.

        Maintains all ratios and form coefficients.

        Args:
            parent: Parent hull definition to scale
            target_lwl: Target waterline length (m)

        Returns:
            New HullDefinition scaled to target LWL
        """
        scaled = copy.deepcopy(parent)

        scale_factor = target_lwl / parent.dimensions.lwl

        # Scale all linear dimensions
        scaled.dimensions.loa *= scale_factor
        scaled.dimensions.lwl = target_lwl
        scaled.dimensions.lpp *= scale_factor
        scaled.dimensions.beam_max *= scale_factor
        scaled.dimensions.beam_wl *= scale_factor
        scaled.dimensions.beam_chine *= scale_factor
        scaled.dimensions.depth *= scale_factor
        scaled.dimensions.draft *= scale_factor
        scaled.dimensions.draft_fwd *= scale_factor
        scaled.dimensions.draft_aft *= scale_factor
        scaled.dimensions.freeboard_bow *= scale_factor
        scaled.dimensions.freeboard_mid *= scale_factor
        scaled.dimensions.freeboard_stern *= scale_factor

        # Scale features
        scaled.features.skeg_height_m *= scale_factor
        scaled.features.tunnel_width_m *= scale_factor
        scaled.features.tunnel_depth_m *= scale_factor

        # Recompute displacement (scales with L^3)
        scaled.compute_displacement()

        # Update ID
        scaled.hull_id = f"{parent.hull_id}-SCALED"

        return scaled

    @staticmethod
    def scale_to_displacement(
        parent: HullDefinition,
        target_displacement_m3: float,
    ) -> HullDefinition:
        """
        Scale hull to target displacement volume.

        Uses cubic root scaling for linear dimensions.

        Args:
            parent: Parent hull definition to scale
            target_displacement_m3: Target displacement volume (m^3)

        Returns:
            New HullDefinition scaled to target displacement
        """
        parent_disp = parent.displacement_m3 or parent.compute_displacement()

        if parent_disp <= 0:
            raise ValueError("Parent hull has zero displacement")

        scale_factor = (target_displacement_m3 / parent_disp) ** (1 / 3)
        target_lwl = parent.dimensions.lwl * scale_factor

        return HullScaler.scale_to_lwl(parent, target_lwl)

    @staticmethod
    def adjust_beam(
        hull: HullDefinition,
        target_beam: float,
    ) -> HullDefinition:
        """
        Adjust beam while maintaining length.

        Updates form coefficients accordingly.

        Args:
            hull: Hull definition to adjust
            target_beam: Target maximum beam (m)

        Returns:
            New HullDefinition with adjusted beam
        """
        adjusted = copy.deepcopy(hull)

        beam_ratio = target_beam / hull.dimensions.beam_max

        adjusted.dimensions.beam_max = target_beam
        adjusted.dimensions.beam_wl *= beam_ratio
        adjusted.dimensions.beam_chine *= beam_ratio

        # Tunnel width scales with beam
        if adjusted.features.has_tunnels:
            adjusted.features.tunnel_width_m *= beam_ratio

        # Recompute displacement
        adjusted.compute_displacement()

        return adjusted

    @staticmethod
    def adjust_draft(
        hull: HullDefinition,
        target_draft: float,
    ) -> HullDefinition:
        """
        Adjust draft while maintaining other dimensions.

        Args:
            hull: Hull definition to adjust
            target_draft: Target design draft (m)

        Returns:
            New HullDefinition with adjusted draft
        """
        adjusted = copy.deepcopy(hull)

        draft_ratio = target_draft / hull.dimensions.draft

        adjusted.dimensions.draft = target_draft
        adjusted.dimensions.draft_fwd *= draft_ratio
        adjusted.dimensions.draft_aft *= draft_ratio

        # Adjust freeboard
        draft_change = target_draft - hull.dimensions.draft
        adjusted.dimensions.freeboard_bow -= draft_change
        adjusted.dimensions.freeboard_mid -= draft_change
        adjusted.dimensions.freeboard_stern -= draft_change

        # Recompute displacement
        adjusted.compute_displacement()

        return adjusted

    @staticmethod
    def adjust_coefficients(
        hull: HullDefinition,
        target_cb: Optional[float] = None,
        target_cp: Optional[float] = None,
        target_lcb: Optional[float] = None,
    ) -> HullDefinition:
        """
        Adjust form coefficients.

        Args:
            hull: Hull definition to adjust
            target_cb: Target block coefficient (optional)
            target_cp: Target prismatic coefficient (optional)
            target_lcb: Target LCB position (optional)

        Returns:
            New HullDefinition with adjusted coefficients
        """
        adjusted = copy.deepcopy(hull)

        if target_cb is not None:
            adjusted.coefficients.cb = target_cb
            # Maintain Cm, adjust Cp
            if adjusted.coefficients.cm > 0:
                adjusted.coefficients.cp = target_cb / adjusted.coefficients.cm

        if target_cp is not None:
            adjusted.coefficients.cp = target_cp
            # Maintain Cm, adjust Cb
            adjusted.coefficients.cb = target_cp * adjusted.coefficients.cm

        if target_lcb is not None:
            adjusted.coefficients.lcb = target_lcb

        # Recompute displacement
        adjusted.compute_displacement()

        return adjusted

    @staticmethod
    def create_from_dimensions(
        parent: HullDefinition,
        lwl: float,
        beam: float,
        draft: float,
    ) -> HullDefinition:
        """
        Create hull from target dimensions using parent as template.

        Args:
            parent: Parent hull to use as template
            lwl: Target waterline length (m)
            beam: Target maximum beam (m)
            draft: Target design draft (m)

        Returns:
            New HullDefinition with specified dimensions
        """
        # Scale to length first
        scaled = HullScaler.scale_to_lwl(parent, lwl)

        # Adjust beam if different from scaled
        if abs(scaled.dimensions.beam_max - beam) > 0.01:
            scaled = HullScaler.adjust_beam(scaled, beam)

        # Adjust draft if different from scaled
        if abs(scaled.dimensions.draft - draft) > 0.01:
            scaled = HullScaler.adjust_draft(scaled, draft)

        return scaled

    @staticmethod
    def interpolate_hulls(
        hull1: HullDefinition,
        hull2: HullDefinition,
        t: float,
    ) -> HullDefinition:
        """
        Interpolate between two hull definitions.

        Args:
            hull1: First hull (t=0)
            hull2: Second hull (t=1)
            t: Interpolation parameter [0, 1]

        Returns:
            New HullDefinition interpolated between hull1 and hull2
        """
        t = max(0.0, min(1.0, t))
        result = copy.deepcopy(hull1)

        # Interpolate dimensions
        d1 = hull1.dimensions
        d2 = hull2.dimensions

        result.dimensions.loa = d1.loa + t * (d2.loa - d1.loa)
        result.dimensions.lwl = d1.lwl + t * (d2.lwl - d1.lwl)
        result.dimensions.lpp = d1.lpp + t * (d2.lpp - d1.lpp)
        result.dimensions.beam_max = d1.beam_max + t * (d2.beam_max - d1.beam_max)
        result.dimensions.beam_wl = d1.beam_wl + t * (d2.beam_wl - d1.beam_wl)
        result.dimensions.beam_chine = d1.beam_chine + t * (d2.beam_chine - d1.beam_chine)
        result.dimensions.depth = d1.depth + t * (d2.depth - d1.depth)
        result.dimensions.draft = d1.draft + t * (d2.draft - d1.draft)

        # Interpolate coefficients
        c1 = hull1.coefficients
        c2 = hull2.coefficients

        result.coefficients.cb = c1.cb + t * (c2.cb - c1.cb)
        result.coefficients.cp = c1.cp + t * (c2.cp - c1.cp)
        result.coefficients.cm = c1.cm + t * (c2.cm - c1.cm)
        result.coefficients.cwp = c1.cwp + t * (c2.cwp - c1.cwp)
        result.coefficients.lcb = c1.lcb + t * (c2.lcb - c1.lcb)

        # Interpolate deadrise
        dr1 = hull1.deadrise
        dr2 = hull2.deadrise

        result.deadrise.deadrise_transom = dr1.deadrise_transom + t * (dr2.deadrise_transom - dr1.deadrise_transom)
        result.deadrise.deadrise_midship = dr1.deadrise_midship + t * (dr2.deadrise_midship - dr1.deadrise_midship)
        result.deadrise.deadrise_bow = dr1.deadrise_bow + t * (dr2.deadrise_bow - dr1.deadrise_bow)

        # Update ID
        result.hull_id = f"INTERP-{hull1.hull_id}-{hull2.hull_id}"
        result.hull_name = f"Interpolated ({hull1.hull_name} - {hull2.hull_name})"

        # Recompute displacement
        result.compute_displacement()

        return result
