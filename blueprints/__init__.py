"""
Blueprint registration for IB Study Companion.

All blueprints are registered without URL prefixes to keep existing URLs stable.
"""

from __future__ import annotations


def register_blueprints(app):
    from blueprints.core import bp as core_bp
    from blueprints.study import bp as study_bp
    from blueprints.upload import bp as upload_bp
    from blueprints.insights import bp as insights_bp
    from blueprints.flashcards import bp as flashcards_bp
    from blueprints.lifecycle import bp as lifecycle_bp
    from blueprints.planner import bp as planner_bp
    from blueprints.parent import bp as parent_bp
    from blueprints.gamification import bp as gamification_bp
    from blueprints.social import bp as social_bp
    from blueprints.teacher import bp as teacher_bp
    from blueprints.notifications import bp as notifications_bp
    from blueprints.billing import bp as billing_bp
    from blueprints.ai import bp as ai_bp
    from blueprints.exam import bp as exam_bp
    from blueprints.export import bp as export_bp
    from blueprints.guest import bp as guest_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(study_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(flashcards_bp)
    app.register_blueprint(lifecycle_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(guest_bp)
