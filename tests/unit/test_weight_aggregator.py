"""
Unit tests for weight aggregation system.

Tests WeightAggregator and LightshipSummary.
"""

import pytest
from magnet.weight.items import SWBSGroup, WeightItem, WeightConfidence
from magnet.weight.aggregator import WeightAggregator, LightshipSummary


class TestWeightAggregator:
    """Tests for WeightAggregator class."""

    def test_empty_aggregator(self):
        """Test empty aggregator raises error on calculate."""
        aggregator = WeightAggregator()
        assert aggregator.item_count == 0
        with pytest.raises(ValueError, match="No weight items added"):
            aggregator.calculate_lightship()

    def test_add_single_item(self):
        """Test adding a single item."""
        aggregator = WeightAggregator()
        item = WeightItem(
            name="Test Item",
            weight_kg=1000.0,
            lcg_m=25.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        )
        aggregator.add_item(item)
        assert aggregator.item_count == 1

    def test_add_multiple_items(self):
        """Test adding multiple items."""
        aggregator = WeightAggregator()
        items = [
            WeightItem(
                name=f"Item {i}",
                weight_kg=1000.0,
                lcg_m=20.0 + i,
                vcg_m=2.0,
                group=SWBSGroup.GROUP_100,
            )
            for i in range(5)
        ]
        aggregator.add_items(items)
        assert aggregator.item_count == 5

    def test_clear(self):
        """Test clearing all items."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Test", weight_kg=1000.0, lcg_m=25.0, vcg_m=2.0,
        ))
        assert aggregator.item_count == 1
        aggregator.clear()
        assert aggregator.item_count == 0

    def test_get_items_by_group(self):
        """Test getting items by SWBS group."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Hull", weight_kg=50000.0, lcg_m=25.0, vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator.add_item(WeightItem(
            name="Engine", weight_kg=5000.0, lcg_m=35.0, vcg_m=1.5,
            group=SWBSGroup.GROUP_200,
        ))
        aggregator.add_item(WeightItem(
            name="Deck", weight_kg=10000.0, lcg_m=25.0, vcg_m=3.5,
            group=SWBSGroup.GROUP_100,
        ))

        hull_items = aggregator.get_items_by_group(SWBSGroup.GROUP_100)
        assert len(hull_items) == 2

        propulsion_items = aggregator.get_items_by_group(SWBSGroup.GROUP_200)
        assert len(propulsion_items) == 1

        electrical_items = aggregator.get_items_by_group(SWBSGroup.GROUP_300)
        assert len(electrical_items) == 0


class TestLightshipCalculation:
    """Tests for lightship calculation."""

    def test_simple_lightship(self):
        """Test simple lightship calculation with one group."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Hull Structure",
            weight_kg=100000.0,  # 100 MT
            lcg_m=25.0,
            vcg_m=3.0,
            group=SWBSGroup.GROUP_100,
            confidence=WeightConfidence.MEDIUM,
        ))
        aggregator.set_margins(margin_percent=0.10)  # 10% margin

        summary = aggregator.calculate_lightship()

        # Base weight is 100 MT
        # Margin is 10 MT
        # Total is 110 MT
        assert summary.base_weight_mt == 100.0
        assert summary.margin_weight_mt == 10.0
        assert summary.lightship_weight_mt == 110.0

    def test_multi_group_lightship(self):
        """Test lightship with multiple SWBS groups."""
        aggregator = WeightAggregator()

        # Group 100 - Hull: 60 MT at LCG=25, VCG=2.5
        aggregator.add_item(WeightItem(
            name="Hull",
            weight_kg=60000.0,
            lcg_m=25.0,
            vcg_m=2.5,
            group=SWBSGroup.GROUP_100,
        ))

        # Group 200 - Propulsion: 20 MT at LCG=35, VCG=1.5
        aggregator.add_item(WeightItem(
            name="Propulsion",
            weight_kg=20000.0,
            lcg_m=35.0,
            vcg_m=1.5,
            group=SWBSGroup.GROUP_200,
        ))

        # Group 300 - Electrical: 5 MT at LCG=30, VCG=3.0
        aggregator.add_item(WeightItem(
            name="Electrical",
            weight_kg=5000.0,
            lcg_m=30.0,
            vcg_m=3.0,
            group=SWBSGroup.GROUP_300,
        ))

        # Group 600 - Outfit: 15 MT at LCG=20, VCG=3.5
        aggregator.add_item(WeightItem(
            name="Outfit",
            weight_kg=15000.0,
            lcg_m=20.0,
            vcg_m=3.5,
            group=SWBSGroup.GROUP_600,
        ))

        aggregator.set_margins(margin_percent=0.10)
        summary = aggregator.calculate_lightship()

        # Base weight: 60 + 20 + 5 + 15 = 100 MT
        assert summary.base_weight_mt == 100.0

        # Margin: 10 MT
        assert summary.margin_weight_mt == 10.0

        # Total: 110 MT
        assert summary.lightship_weight_mt == 110.0

        # Verify group summaries exist
        assert SWBSGroup.GROUP_100 in summary.group_summaries
        assert SWBSGroup.GROUP_200 in summary.group_summaries
        assert SWBSGroup.GROUP_300 in summary.group_summaries
        assert SWBSGroup.GROUP_600 in summary.group_summaries

        # Check group weights
        assert summary.get_group_weight_mt(SWBSGroup.GROUP_100) == 60.0
        assert summary.get_group_weight_mt(SWBSGroup.GROUP_200) == 20.0

    def test_weighted_lcg_calculation(self):
        """Test moment-weighted LCG calculation."""
        aggregator = WeightAggregator()

        # Item 1: 20 MT at LCG=20
        aggregator.add_item(WeightItem(
            name="Forward",
            weight_kg=20000.0,
            lcg_m=20.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))

        # Item 2: 30 MT at LCG=30
        aggregator.add_item(WeightItem(
            name="Aft",
            weight_kg=30000.0,
            lcg_m=30.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))

        aggregator.set_margins(margin_percent=0.0)  # No margin for simplicity
        summary = aggregator.calculate_lightship()

        # Expected LCG: (20000*20 + 30000*30) / 50000 = (400000 + 900000) / 50000 = 26.0
        assert abs(summary.base_lcg_m - 26.0) < 0.01

    def test_weighted_vcg_calculation(self):
        """Test moment-weighted VCG calculation."""
        aggregator = WeightAggregator()

        # Item 1: 40 MT at VCG=2.0
        aggregator.add_item(WeightItem(
            name="Low",
            weight_kg=40000.0,
            lcg_m=25.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))

        # Item 2: 10 MT at VCG=6.0
        aggregator.add_item(WeightItem(
            name="High",
            weight_kg=10000.0,
            lcg_m=25.0,
            vcg_m=6.0,
            group=SWBSGroup.GROUP_600,
        ))

        aggregator.set_margins(margin_percent=0.0)
        summary = aggregator.calculate_lightship()

        # Expected VCG: (40000*2.0 + 10000*6.0) / 50000 = (80000 + 60000) / 50000 = 2.8
        assert abs(summary.base_vcg_m - 2.8) < 0.01

    def test_vessel_type_margins(self):
        """Test margin percentage varies by vessel type."""
        aggregator1 = WeightAggregator()
        aggregator1.add_item(WeightItem(
            name="Hull", weight_kg=100000.0, lcg_m=25.0, vcg_m=2.5,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator1.set_margins(vessel_type="patrol")  # 8%
        summary1 = aggregator1.calculate_lightship()

        aggregator2 = WeightAggregator()
        aggregator2.add_item(WeightItem(
            name="Hull", weight_kg=100000.0, lcg_m=25.0, vcg_m=2.5,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator2.set_margins(vessel_type="yacht")  # 15%
        summary2 = aggregator2.calculate_lightship()

        # Patrol should have lower margin than yacht
        assert summary1.margin_weight_mt < summary2.margin_weight_mt


class TestLightshipSummary:
    """Tests for LightshipSummary dataclass."""

    def test_to_dict(self):
        """Test LightshipSummary serialization."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Hull", weight_kg=50000.0, lcg_m=25.0, vcg_m=2.5,
            group=SWBSGroup.GROUP_100, confidence=WeightConfidence.MEDIUM,
        ))
        aggregator.set_margins(margin_percent=0.10)
        summary = aggregator.calculate_lightship()

        d = summary.to_dict()
        assert "lightship" in d
        assert d["lightship"]["weight_mt"] == 55.0
        assert "base" in d
        assert d["base"]["weight_mt"] == 50.0
        assert "margin" in d
        assert d["margin"]["weight_mt"] == 5.0
        assert "groups" in d

    def test_get_group_percentage(self):
        """Test calculating group percentage of base weight."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Hull", weight_kg=60000.0, lcg_m=25.0, vcg_m=2.5,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator.add_item(WeightItem(
            name="Engine", weight_kg=40000.0, lcg_m=35.0, vcg_m=1.5,
            group=SWBSGroup.GROUP_200,
        ))
        aggregator.set_margins(margin_percent=0.0)
        summary = aggregator.calculate_lightship()

        # Hull is 60% of 100 MT base weight
        assert abs(summary.get_group_percentage(SWBSGroup.GROUP_100) - 60.0) < 0.1

        # Propulsion is 40% of 100 MT base weight
        assert abs(summary.get_group_percentage(SWBSGroup.GROUP_200) - 40.0) < 0.1

    def test_average_confidence(self):
        """Test average confidence calculation."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Item 1", weight_kg=1000.0, lcg_m=25.0, vcg_m=2.0,
            group=SWBSGroup.GROUP_100, confidence=WeightConfidence.LOW,  # 0.5
        ))
        aggregator.add_item(WeightItem(
            name="Item 2", weight_kg=1000.0, lcg_m=25.0, vcg_m=2.0,
            group=SWBSGroup.GROUP_100, confidence=WeightConfidence.HIGH,  # 0.85
        ))
        aggregator.set_margins(margin_percent=0.0)
        summary = aggregator.calculate_lightship()

        # Average: (0.5 + 0.85) / 2 = 0.675
        assert abs(summary.average_confidence - 0.675) < 0.01
