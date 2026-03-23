"""
Scoring engine for evaluating schedules against soft constraints.
"""
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from constraints import Constraint, evaluate_constraint, get_constraint_display_name


@dataclass
class ScoreResult:
    """Result of scoring a schedule"""
    total_score: int = 0
    max_possible_score: int = 0
    percentage: float = 0.0
    satisfied_constraints: List[Constraint] = field(default_factory=list)
    unsatisfied_constraints: List[Constraint] = field(default_factory=list)
    breakdown: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "max_possible_score": self.max_possible_score,
            "percentage": self.percentage,
            "satisfied": [c.to_dict() for c in self.satisfied_constraints],
            "unsatisfied": [c.to_dict() for c in self.unsatisfied_constraints],
            "breakdown": self.breakdown
        }


def calculate_score(periods: List, sections: List, constraints: List[Constraint]) -> ScoreResult:
    """
    Calculate the score for a schedule given a list of constraints.
    
    Args:
        periods: List of Period objects with assigned sections
        sections: List of all Section objects
        constraints: List of Constraint objects to evaluate
    
    Returns:
        ScoreResult with total score, max possible, percentage, and breakdown
    """
    result = ScoreResult()
    
    if not constraints:
        result.percentage = 100.0
        return result
    
    satisfied = []
    unsatisfied = []
    breakdown = []
    
    for constraint in constraints:
        is_satisfied = evaluate_constraint(constraint, periods, sections)
        
        constraint_info = {
            "id": constraint.id,
            "type": constraint.constraint_type,
            "display_name": get_constraint_display_name(constraint.constraint_type),
            "applies_to": constraint.applies_to,
            "weight": constraint.weight,
            "satisfied": is_satisfied,
            "parameters": constraint.parameters
        }
        
        if is_satisfied:
            satisfied.append(constraint)
            result.total_score += constraint.weight
        else:
            unsatisfied.append(constraint)
        
        result.max_possible_score += constraint.weight
        breakdown.append(constraint_info)
    
    result.satisfied_constraints = satisfied
    result.unsatisfied_constraints = unsatisfied
    result.breakdown = breakdown
    
    if result.max_possible_score > 0:
        result.percentage = (result.total_score / result.max_possible_score) * 100
    else:
        result.percentage = 100.0
    
    return result


def rank_schedules(schedule_results: List[Tuple[Any, ScoreResult]]) -> List[Tuple[Any, ScoreResult]]:
    """
    Rank schedules by score (highest first).
    
    Args:
        schedule_results: List of (schedule_data, score_result) tuples
    
    Returns:
        Sorted list with highest scores first
    """
    return sorted(schedule_results, key=lambda x: x[1].total_score, reverse=True)


def get_top_n_schedules(schedule_results: List[Tuple[Any, ScoreResult]], n: int = 3) -> List[Tuple[Any, ScoreResult]]:
    """
    Get the top N schedules by score.
    
    Args:
        schedule_results: List of (schedule_data, score_result) tuples
        n: Number of top schedules to return
    
    Returns:
        List of top N (schedule_data, score_result) tuples
    """
    ranked = rank_schedules(schedule_results)
    return ranked[:n]


def format_score_breakdown(score_result: ScoreResult) -> str:
    """Format the score breakdown as a readable string"""
    lines = []
    lines.append(f"Score: {score_result.total_score}/{score_result.max_possible_score} ({score_result.percentage:.1f}%)")
    lines.append("")
    lines.append("Constraint Breakdown:")
    lines.append("-" * 50)
    
    for item in score_result.breakdown:
        status = "✓" if item["satisfied"] else "✗"
        lines.append(f"  {status} {item['display_name']} ({item['applies_to']}): {item['weight']} pts")
    
    return "\n".join(lines)