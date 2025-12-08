"""
Unit tests for weight item data structures.

Tests SWBSGroup, WeightConfidence, WeightItem, and GroupSummary.
"""

import pytest
from magnet.weight.items import (
    SWBSGroup,
    WeightConfidence,
    WeightItem,
    GroupSummary,
    SWBS_GROUP_NAMES,
    create_weight_item,
)


class TestSWBSGroup:
    """Tests for SWBSGroup enum."""

    def test_group_values(self):
        """Test SWBS group numeric values."""
        assert SWBSGroup.GROUP_100.value == 100
        assert SWBSGroup.GROUP_200.value == 200
        assert SWBSGroup.GROUP_300.value == 300
        assert SWBSGroup.GROUP_400.value == 400
        assert SWBSGroup.GROUP_500.value == 500
        assert SWBSGroup.GROUP_600.value == 600
        assert SWBSGroup.GROUP_700.value == 700
        assert SWBSGroup.MARGIN.value == 999

    def test_group_names(self):
        """Test human-readable group names."""
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_100] == "Hull Structure"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_200] == "Propulsion Plant"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_300] == "Electrical Plant"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_400] == "Command & Surveillance"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_500] == "Auxiliary Systems"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_600] == "Outfit & Furnishings"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_700] == "Armament"
        assert SWBS_GROUP_NAMES[SWBSGroup.MARGIN] == "Design/Growth Margin"

    def test_group_from_int(self):
        """Test creating group from integer value."""
        assert SWBSGroup(100) == SWBSGroup.GROUP_100
        assert SWBSGroup(200) == SWBSGroup.GROUP_200


class TestWeightConfidence:
    """Tests for WeightConfidence enum."""

    def test_confidence_values(self):
        """Test confidence numeric values."""
        assert WeightConfidence.VERY_LOW.value == 0.3
        assert WeightConfidence.LOW.value == 0.5
        assert WeightConfidence.MEDIUM.value == 0.7
        assert WeightConfidence.HIGH.value == 0.85
        assert WeightConfidence.VERY_HIGH.value == 0.95

    def test_confidence_ordering(self):
        """Test confidence values are ordered correctly."""
        assert WeightConfidence.VERY_LOW.value < WeightConfidence.LOW.value
        assert WeightConfidence.LOW.value < WeightConfidence.MEDIUM.value
        assert WeightConfidence.MEDIUM.value < WeightConfidence.HIGH.value
        assert WeightConfidence.HIGH.value < WeightConfidence.VERY_HIGH.value


class TestWeightItem:
    """Tests for WeightItem dataclass."""

    def test_create_basic(self):
        """Test creating a basic weight item."""
        item = WeightItem(
            name="Shell Plating",
            weight_kg=50000.0,
            lcg_m=25.0,
            vcg_m=2.0,
        )
        assert item.name == "Shell Plating"
        assert item.weight_kg == 50000.0
        assert item.lcg_m == 25.0
        assert item.vcg_m == 2.0
        assert item.tcg_m == 0.0  # Default
        assert item.group == SWBSGroup.GROUP_100  # Default
        assert item.confidence == WeightConfidence.MEDIUM  # Default

    def test_create_with_all_fields(self):
        """Test creating item with all fields."""
        item = WeightItem(
            name="Main Engine Port",
            weight_kg=5000.0,
            lcg_m=35.0,
            vcg_m=1.5,
            tcg_m=-2.0,
            group=SWBSGroup.GROUP_200,
            subgroup=210,
            confidence=WeightConfidence.HIGH,
            notes="CAT 3516C",
        )
        assert item.group == SWBSGroup.GROUP_200
        assert item.subgroup == 210
        assert item.tcg_m == -2.0
        assert item.confidence == WeightConfidence.HIGH
        assert item.notes == "CAT 3516C"

    def test_weight_mt_property(self):
        """Test weight conversion to metric tons."""
        item = WeightItem(
            name="Test",
            weight_kg=1500.0,
            lcg_m=25.0,
            vcg_m=2.0,
        )
        assert item.weight_mt == 1.5

    def test_moment_properties(self):
        """Test moment calculations."""
        item = WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=10.0,
            vcg_m=5.0,
            tcg_m=2.0,
        )
        assert item.lcg_moment_kg_m == 10000.0  # 1000 * 10
        assert item.vcg_moment_kg_m == 5000.0   # 1000 * 5
        assert item.tcg_moment_kg_m == 2000.0   # 1000 * 2

    def test_group_number_property(self):
        """Test group number property."""
        item = WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=10.0,
            vcg_m=5.0,
            group=SWBSGroup.GROUP_300,
        )
        assert item.group_number == 300

    def test_confidence_value_property(self):
        """Test confidence value property."""
        item = WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=10.0,
            vcg_m=5.0,
            confidence=WeightConfidence.HIGH,
        )
        assert item.confidence_value == 0.85

    def test_to_dict(self):
        """Test serialization to dictionary."""
        item = WeightItem(
            name="Test Item",
            weight_kg=2000.0,
            lcg_m=20.0,
            vcg_m=3.0,
            tcg_m=0.5,
            group=SWBSGroup.GROUP_100,
            subgroup=110,
            confidence=WeightConfidence.MEDIUM,
            notes="Test note",
        )
        d = item.to_dict()
        assert d["name"] == "Test Item"
        assert d["weight_kg"] == 2000.0
        assert d["weight_mt"] == 2.0
        assert d["lcg_m"] == 20.0
        assert d["vcg_m"] == 3.0
        assert d["tcg_m"] == 0.5
        assert d["group"] == 100
        assert d["group_name"] == "Hull Structure"
        assert d["subgroup"] == 110
        assert d["confidence"] == 0.7
        assert d["notes"] == "Test note"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {
            "name": "Restored Item",
            "weight_kg": 3000.0,
            "lcg_m": 30.0,
            "vcg_m": 4.0,
            "tcg_m": -1.0,
            "group": 200,
            "subgroup": 220,
            "confidence": 0.85,
            "notes": "Restored note",
        }
        item = WeightItem.from_dict(d)
        assert item.name == "Restored Item"
        assert item.weight_kg == 3000.0
        assert item.lcg_m == 30.0
        assert item.vcg_m == 4.0
        assert item.tcg_m == -1.0
        assert item.group == SWBSGroup.GROUP_200
        assert item.subgroup == 220
        assert item.confidence == WeightConfidence.HIGH
        assert item.notes == "Restored note"

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = WeightItem(
            name="Roundtrip Test",
            weight_kg=5000.0,
            lcg_m=25.0,
            vcg_m=2.5,
            tcg_m=1.0,
            group=SWBSGroup.GROUP_500,
            subgroup=510,
            confidence=WeightConfidence.LOW,
            notes="Roundtrip note",
        )
        d = original.to_dict()
        restored = WeightItem.from_dict(d)
        assert restored.name == original.name
        assert restored.weight_kg == original.weight_kg
        assert restored.lcg_m == original.lcg_m
        assert restored.vcg_m == original.vcg_m
        assert restored.tcg_m == original.tcg_m
        assert restored.group == original.group
        assert restored.subgroup == original.subgroup
        assert restored.confidence == original.confidence
        assert restored.notes == original.notes


class TestCreateWeightItem:
    """Tests for create_weight_item factory function."""

    def test_create_valid_item(self):
        """Test creating valid item via factory."""
        item = create_weight_item(
            name="Factory Test",
            weight_kg=1000.0,
            lcg_m=20.0,
            vcg_m=3.0,
            group=SWBSGroup.GROUP_100,
        )
        assert item.name == "Factory Test"
        assert item.weight_kg == 1000.0

    def test_negative_weight_raises(self):
        """Test that negative weight raises ValueError."""
        with pytest.raises(ValueError, match="Weight cannot be negative"):
            create_weight_item(
                name="Invalid",
                weight_kg=-100.0,
                lcg_m=20.0,
                vcg_m=3.0,
                group=SWBSGroup.GROUP_100,
            )


class TestGroupSummary:
    """Tests for GroupSummary dataclass."""

    def test_from_empty_items(self):
        """Test creating summary from empty items list."""
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, [])
        assert summary.group == SWBSGroup.GROUP_100
        assert summary.total_weight_mt == 0.0
        assert summary.item_count == 0
        assert summary.average_confidence == 0.0

    def test_from_single_item(self):
        """Test creating summary from single item."""
        item = WeightItem(
            name="Single Item",
            weight_kg=5000.0,
            lcg_m=25.0,
            vcg_m=2.0,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_100,
            confidence=WeightConfidence.HIGH,
        )
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, [item])
        assert summary.total_weight_mt == 5.0
        assert summary.lcg_m == 25.0
        assert summary.vcg_m == 2.0
        assert summary.tcg_m == 0.0
        assert summary.item_count == 1
        assert summary.average_confidence == 0.85

    def test_from_multiple_items(self):
        """Test creating summary from multiple items with weighted averaging."""
        items = [
            WeightItem(
                name="Item 1",
                weight_kg=2000.0,
                lcg_m=20.0,  # Moment: 40000
                vcg_m=1.0,   # Moment: 2000
                group=SWBSGroup.GROUP_100,
                confidence=WeightConfidence.MEDIUM,
            ),
            WeightItem(
                name="Item 2",
                weight_kg=3000.0,
                lcg_m=30.0,  # Moment: 90000
                vcg_m=2.0,   # Moment: 6000
                group=SWBSGroup.GROUP_100,
                confidence=WeightConfidence.HIGH,
            ),
        ]
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, items)

        # Total: 5000 kg = 5 MT
        assert summary.total_weight_mt == 5.0

        # LCG: (40000 + 90000) / 5000 = 26.0
        assert summary.lcg_m == 26.0

        # VCG: (2000 + 6000) / 5000 = 1.6
        assert summary.vcg_m == 1.6

        assert summary.item_count == 2

        # Average confidence: (0.7 + 0.85) / 2 = 0.775
        assert abs(summary.average_confidence - 0.775) < 0.001

    def test_to_dict(self):
        """Test GroupSummary serialization."""
        summary = GroupSummary(
            group=SWBSGroup.GROUP_200,
            name="Propulsion Plant",
            total_weight_mt=25.0,
            lcg_m=35.0,
            vcg_m=1.5,
            tcg_m=0.0,
            item_count=5,
            average_confidence=0.8,
        )
        d = summary.to_dict()
        assert d["group"] == 200
        assert d["name"] == "Propulsion Plant"
        assert d["total_weight_mt"] == 25.0
        assert d["lcg_m"] == 35.0
        assert d["vcg_m"] == 1.5
        assert d["item_count"] == 5
        assert d["average_confidence"] == 0.8
