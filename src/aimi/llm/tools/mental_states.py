"""Mental state management tools for LLM."""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.repositories.mental_states import MentalStateRepository
from aimi.db.models.enums import MentalStateMood

logger = logging.getLogger(__name__)


class MentalStateTools:
    """Tools for LLM to manage user mental state polling."""

    def __init__(self, db_session: AsyncSession, user_id: UUID, chat_id: UUID):
        self.db = db_session
        self.user_id = user_id
        self.chat_id = chat_id
        self.repo = MentalStateRepository(db_session)

    async def create_daily_poll(
        self,
        date_str: str | None = None,
    ) -> Dict[str, Any]:
        """Create a daily mental state poll for the user."""
        try:
            # Parse date if provided, otherwise use today
            if date_str:
                try:
                    poll_date = datetime.fromisoformat(date_str)
                except ValueError:
                    return {"error": f"Invalid date format: {date_str}. Use ISO format"}
            else:
                poll_date = datetime.utcnow()

            # Check if poll already exists for this date
            target_date = poll_date.date()
            existing_poll = await self.repo.get_by_user_and_date(self.user_id, target_date)
            if existing_poll:
                return {"error": f"Mental state poll already exists for {target_date}"}

            # Create new poll
            mental_state = await self.repo.create_mental_state(
                user_id=self.user_id,
                date=poll_date,
            )

            await self.db.commit()

            logger.info(f"Created daily mental state poll for user {self.user_id} on {target_date}")

            return {
                "mental_state_id": str(mental_state.id),
                "user_id": str(mental_state.user_id),
                "date": mental_state.date.isoformat(),
                "question_asked_at": mental_state.question_asked_at.isoformat(),
                "status": "pending",
            }

        except Exception as e:
            logger.error(f"Failed to create daily poll: {e}")
            await self.db.rollback()
            return {"error": f"Failed to create daily poll: {str(e)}"}

    async def respond_to_poll(
        self,
        mental_state_id: str,
        mood: str | None = None,
        readiness_level: int | None = None,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        """Respond to a mental state poll."""
        try:
            # Get mental state
            mental_state = await self.repo.get_by_id(UUID(mental_state_id))
            if not mental_state or mental_state.user_id != self.user_id:
                return {"error": f"Mental state poll {mental_state_id} not found or not owned by user"}

            # Check if already responded
            if mental_state.responded_at:
                return {"error": "Mental state poll has already been responded to"}

            # Validate mood if provided
            mood_enum = None
            if mood:
                try:
                    mood_enum = MentalStateMood(mood)
                except ValueError:
                    valid_moods = [e.value for e in MentalStateMood]
                    return {"error": f"Invalid mood: {mood}. Must be one of {valid_moods}"}

            # Validate readiness level if provided
            if readiness_level is not None:
                if not (1 <= readiness_level <= 10):
                    return {"error": "Readiness level must be between 1 and 10"}

            # Update mental state with response
            await self.repo.update_mental_state(
                mental_state,
                mood=mood_enum,
                readiness_level=readiness_level,
                notes=notes,
                responded_at=datetime.utcnow(),
            )

            await self.db.commit()

            logger.info(f"Updated mental state poll {mental_state_id} with user response")

            return {
                "mental_state_id": str(mental_state.id),
                "date": mental_state.date.isoformat(),
                "mood": mood_enum if mood_enum else None,
                "readiness_level": readiness_level,
                "notes": notes,
                "responded_at": mental_state.responded_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to respond to poll: {e}")
            await self.db.rollback()
            return {"error": f"Failed to respond to poll: {str(e)}"}

    async def get_user_mental_states(
        self,
        limit: int = 30,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Dict[str, Any]:
        """Get mental state history for the user."""
        try:
            # Parse date filters if provided
            start_dt = None
            end_dt = None

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date)
                except ValueError:
                    return {"error": f"Invalid start_date format: {start_date}. Use ISO format"}

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date)
                except ValueError:
                    return {"error": f"Invalid end_date format: {end_date}. Use ISO format"}

            # Get mental states using repository
            mental_states = await self.repo.get_user_mental_states(
                user_id=self.user_id,
                limit=limit,
                start_date=start_dt,
                end_date=end_dt,
            )

            mental_states_data = []
            for state in mental_states:
                mental_states_data.append({
                    "mental_state_id": str(state.id),
                    "date": state.date.isoformat(),
                    "mood": state.mood if state.mood else None,
                    "readiness_level": state.readiness_level,
                    "notes": state.notes,
                    "question_asked_at": state.question_asked_at.isoformat(),
                    "responded_at": state.responded_at.isoformat() if state.responded_at else None,
                    "status": "completed" if state.responded_at else "pending",
                })

            return {
                "mental_states": mental_states_data,
                "total": len(mental_states_data),
            }

        except Exception as e:
            logger.error(f"Failed to get user mental states: {e}")
            return {"error": f"Failed to get user mental states: {str(e)}"}

    async def get_unanswered_polls(
        self,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get unanswered mental state polls for the user."""
        try:
            # Get unanswered polls using repository
            polls = await self.repo.get_unanswered_polls(
                user_id=self.user_id,
                limit=limit
            )

            polls_data = []
            for poll in polls:
                polls_data.append({
                    "mental_state_id": str(poll.id),
                    "date": poll.date.isoformat(),
                    "question_asked_at": poll.question_asked_at.isoformat(),
                    "days_pending": (datetime.utcnow() - poll.question_asked_at).days,
                })

            return {
                "unanswered_polls": polls_data,
                "total": len(polls_data),
            }

        except Exception as e:
            logger.error(f"Failed to get unanswered polls: {e}")
            return {"error": f"Failed to get unanswered polls: {str(e)}"}

    async def get_mood_trends(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get mood trends over the specified period."""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = datetime.utcnow().replace(day=1)  # Start of current month
            if days:
                from datetime import timedelta
                start_date = end_date - timedelta(days=days)

            # Get mental states for the period
            mental_states = await self.repo.get_user_mental_states(
                user_id=self.user_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Analyze trends
            moods = [state.mood for state in mental_states if state.mood and state.responded_at]
            readiness_levels = [state.readiness_level for state in mental_states if state.readiness_level is not None and state.responded_at]

            mood_counts = {}
            for mood in moods:
                mood_counts[mood] = mood_counts.get(mood, 0) + 1

            avg_readiness = sum(readiness_levels) / len(readiness_levels) if readiness_levels else None

            return {
                "period_days": days,
                "total_responses": len([s for s in mental_states if s.responded_at]),
                "total_polls": len(mental_states),
                "response_rate": len([s for s in mental_states if s.responded_at]) / len(mental_states) if mental_states else 0,
                "mood_distribution": mood_counts,
                "average_readiness_level": round(avg_readiness, 1) if avg_readiness else None,
                "recent_moods": moods[-7:] if moods else [],  # Last 7 mood entries
            }

        except Exception as e:
            logger.error(f"Failed to get mood trends: {e}")
            return {"error": f"Failed to get mood trends: {str(e)}"}


__all__ = ["MentalStateTools"]