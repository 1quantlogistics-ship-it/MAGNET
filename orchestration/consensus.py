"""
MAGNET Consensus Engine
=======================

Implements voting and consensus mechanisms for multi-agent agreement.

From Operations Guide:
- Threshold for consensus: 0.66 (2/3 majority)
- Agents can vote: APPROVE, REVISE, REJECT
- Weighted voting based on agent confidence
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from memory.schemas import VoteType, AgentVoteSchema


class ConsensusStatus(str, Enum):
    """Status of consensus process."""
    PENDING = "pending"
    ACHIEVED = "achieved"
    REVISION_NEEDED = "revision_needed"
    REJECTED = "rejected"
    INSUFFICIENT_VOTES = "insufficient_votes"


@dataclass
class ConsensusResult:
    """Result of consensus evaluation."""

    status: ConsensusStatus
    approval_ratio: float
    weighted_approval: float
    total_votes: int
    votes_by_type: Dict[VoteType, int]
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_approved(self) -> bool:
        """Check if consensus approves the proposal."""
        return self.status == ConsensusStatus.ACHIEVED

    @property
    def needs_revision(self) -> bool:
        """Check if proposal needs revision."""
        return self.status == ConsensusStatus.REVISION_NEEDED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "approval_ratio": self.approval_ratio,
            "weighted_approval": self.weighted_approval,
            "total_votes": self.total_votes,
            "votes_by_type": {k.value: v for k, v in self.votes_by_type.items()},
            "concerns": self.concerns,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class ConsensusEngine:
    """
    Multi-agent consensus engine.

    Evaluates votes from multiple agents and determines
    whether consensus has been achieved.
    """

    # Default threshold for approval (2/3 majority)
    DEFAULT_THRESHOLD = 0.66

    # Minimum votes required for valid consensus
    MIN_VOTES = 2

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        min_votes: int = MIN_VOTES,
        use_weighted: bool = True,
    ):
        """
        Initialize consensus engine.

        Args:
            threshold: Approval ratio threshold (0.0-1.0)
            min_votes: Minimum votes required
            use_weighted: Use confidence-weighted voting
        """
        self.threshold = threshold
        self.min_votes = min_votes
        self.use_weighted = use_weighted

        # Track voting history
        self._vote_history: List[AgentVoteSchema] = []

    def evaluate(
        self,
        votes: List[AgentVoteSchema],
        proposal_id: Optional[str] = None,
    ) -> ConsensusResult:
        """
        Evaluate votes for a proposal.

        Args:
            votes: List of agent votes
            proposal_id: Optional proposal ID to filter votes

        Returns:
            ConsensusResult with evaluation outcome
        """
        # Filter by proposal if specified
        if proposal_id:
            votes = [v for v in votes if v.proposal_id == proposal_id]

        # Check minimum votes
        if len(votes) < self.min_votes:
            return ConsensusResult(
                status=ConsensusStatus.INSUFFICIENT_VOTES,
                approval_ratio=0.0,
                weighted_approval=0.0,
                total_votes=len(votes),
                votes_by_type=self._count_votes(votes),
                concerns=["Insufficient votes for consensus"],
            )

        # Count votes by type
        votes_by_type = self._count_votes(votes)

        # Calculate approval ratios
        approval_ratio = self._calculate_approval_ratio(votes)
        weighted_approval = self._calculate_weighted_approval(votes) if self.use_weighted else approval_ratio

        # Collect concerns and recommendations
        concerns = self._collect_concerns(votes)
        recommendations = self._collect_recommendations(votes)

        # Determine status
        status = self._determine_status(
            votes_by_type,
            weighted_approval if self.use_weighted else approval_ratio,
        )

        return ConsensusResult(
            status=status,
            approval_ratio=approval_ratio,
            weighted_approval=weighted_approval,
            total_votes=len(votes),
            votes_by_type=votes_by_type,
            concerns=concerns,
            recommendations=recommendations,
        )

    def _count_votes(self, votes: List[AgentVoteSchema]) -> Dict[VoteType, int]:
        """Count votes by type."""
        counts = {VoteType.APPROVE: 0, VoteType.REVISE: 0, VoteType.REJECT: 0}
        for vote in votes:
            counts[vote.vote] = counts.get(vote.vote, 0) + 1
        return counts

    def _calculate_approval_ratio(self, votes: List[AgentVoteSchema]) -> float:
        """Calculate simple approval ratio."""
        if not votes:
            return 0.0

        approvals = sum(1 for v in votes if v.vote == VoteType.APPROVE)
        return approvals / len(votes)

    def _calculate_weighted_approval(self, votes: List[AgentVoteSchema]) -> float:
        """Calculate confidence-weighted approval ratio."""
        if not votes:
            return 0.0

        weighted_approvals = 0.0
        total_weight = 0.0

        for vote in votes:
            weight = vote.confidence
            total_weight += weight

            if vote.vote == VoteType.APPROVE:
                weighted_approvals += weight
            elif vote.vote == VoteType.REVISE:
                # Partial credit for revise votes
                weighted_approvals += weight * 0.3

        return weighted_approvals / total_weight if total_weight > 0 else 0.0

    def _collect_concerns(self, votes: List[AgentVoteSchema]) -> List[str]:
        """Collect all concerns from votes."""
        concerns = []
        for vote in votes:
            if vote.concerns:
                concerns.extend(vote.concerns)
        return concerns

    def _collect_recommendations(self, votes: List[AgentVoteSchema]) -> List[str]:
        """Collect recommendations from revise/reject votes."""
        recommendations = []
        for vote in votes:
            if vote.vote in (VoteType.REVISE, VoteType.REJECT):
                if vote.reasoning:
                    recommendations.append(f"{vote.agent_id}: {vote.reasoning}")
        return recommendations

    def _determine_status(
        self,
        votes_by_type: Dict[VoteType, int],
        approval_score: float,
    ) -> ConsensusStatus:
        """Determine consensus status from votes."""
        # Check for any rejection
        if votes_by_type.get(VoteType.REJECT, 0) > 0:
            # If more than 1/3 reject, it's rejected
            total = sum(votes_by_type.values())
            reject_ratio = votes_by_type[VoteType.REJECT] / total
            if reject_ratio > (1 - self.threshold):
                return ConsensusStatus.REJECTED

        # Check approval threshold
        if approval_score >= self.threshold:
            return ConsensusStatus.ACHIEVED

        # Otherwise revision needed
        return ConsensusStatus.REVISION_NEEDED

    def add_vote(self, vote: AgentVoteSchema) -> None:
        """Add a vote to history."""
        self._vote_history.append(vote)

    def get_votes_for_proposal(self, proposal_id: str) -> List[AgentVoteSchema]:
        """Get all votes for a specific proposal."""
        return [v for v in self._vote_history if v.proposal_id == proposal_id]

    def clear_history(self) -> None:
        """Clear vote history."""
        self._vote_history.clear()


# Convenience function
def create_consensus_engine(**kwargs) -> ConsensusEngine:
    """Create a ConsensusEngine instance."""
    return ConsensusEngine(**kwargs)
