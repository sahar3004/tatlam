from __future__ import annotations

import os
from typing import Any, cast

from flask import Response, redirect, request, url_for
from flask.typing import ResponseReturnValue
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from wtforms import TextAreaField


def init_admin(app: Any, Base: Any, session: Any, table_name: str, has_status: bool) -> Admin:
    # JSON-like TEXT columns we want to show as textareas in forms
    JSON_TEXT_FIELDS = [
        "steps",
        "required_response",
        "debrief_points",
        "comms",
        "decision_points",
        "escalation_conditions",
        "lessons_learned",
        "variations",
        "validation",
    ]
    class SecureIndex(AdminIndexView):  # type: ignore[misc]
        def is_accessible(self) -> bool:
            auth = request.authorization
            admin_user = os.getenv("ADMIN_USER")
            admin_pass = os.getenv("ADMIN_PASS")
            if not admin_user or not admin_pass:
                return True
            return bool(auth and auth.username == admin_user and auth.password == admin_pass)

        def inaccessible_callback(self, name: str, **kwargs: Any) -> ResponseReturnValue:
            return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})

        @expose("/")  # type: ignore[misc]
        def index(self) -> ResponseReturnValue:
            # Redirect to Pending view for a focused workflow
            try:
                return redirect(url_for("pending.index_view"))
            except Exception:
                return cast(ResponseReturnValue, super().index())

    class ScenarioAdmin(ModelView):  # type: ignore[misc]
        page_size = 20
        can_view_details = True
        details_modal = True
        edit_modal = True

        # Quick search / filters / sorting
        column_searchable_list = ("title", "category", "location")
        column_sortable_list = ("id", "title", "created_at")

        # Hebrew labels for clarity
        column_labels = {
            "id": "מזהה",
            "title": "כותרת",
            "category": "קטגוריה",
            "status": "סטטוס",
            "approved_by": "אושר ע""י",
            "owner": "בעלים",
            "created_at": "נוצר",
        }

        # Render JSON-like fields as large textareas in the edit form
        form_overrides = {name: TextAreaField for name in JSON_TEXT_FIELDS}
        form_widget_args = {name: {"rows": 6, "style": "direction:rtl;"} for name in JSON_TEXT_FIELDS}

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            cols: list[str] = ["id", "title", "category"]
            if has_status and hasattr(self.model, "status"):
                cols.append("status")
            if hasattr(self.model, "approved_by"):
                cols.append("approved_by")
            if hasattr(self.model, "owner"):
                cols.append("owner")
            if hasattr(self.model, "created_at"):
                cols.append("created_at")
            self.column_list = tuple(cols)

            flt: list[str] = []
            for name in ("category", "owner", "status", "approved_by"):
                if hasattr(self.model, name):
                    flt.append(name)
            self.column_filters = tuple(flt)

        @action("approve", "Approve", "Approve selected items?")  # type: ignore[misc]
        def action_approve(self, ids: list[int]) -> None:
            q = self.session.query(self.model).filter(self.model.id.in_(ids))
            count = 0
            for obj in q.all():
                if has_status and hasattr(obj, "status"):
                    obj.status = "approved"
                if hasattr(obj, "approved_by"):
                    try:
                        current = (obj.approved_by or "").strip()
                    except Exception:
                        current = ""
                    if not current:
                        obj.approved_by = "Admin"
                count += 1
            self.session.commit()
            self.flash(f"אושרו {count} פריטים", "success")

        @action("to_pending", "החזר ל‑Pending", "להחזיר את הפריטים שנבחרו למצב Pending?")  # type: ignore[misc]
        def action_to_pending(self, ids: list[int]) -> None:
            q = self.session.query(self.model).filter(self.model.id.in_(ids))
            count = 0
            for obj in q.all():
                if has_status and hasattr(obj, "status"):
                    obj.status = "pending"
                if hasattr(obj, "approved_by"):
                    obj.approved_by = ""
                count += 1
            self.session.commit()
            self.flash(f"עודכנו {count} פריטים ל‑Pending", "info")

        @action("reject", "דחה", "לדחות את הפריטים שנבחרו?")  # type: ignore[misc]
        def action_reject(self, ids: list[int]) -> None:
            q = self.session.query(self.model).filter(self.model.id.in_(ids))
            count = 0
            for obj in q.all():
                if has_status and hasattr(obj, "status"):
                    obj.status = "rejected"
                count += 1
            self.session.commit()
            self.flash(f"נדחו {count} פריטים", "warning")

    class PendingAdmin(ScenarioAdmin):
        def is_visible(self) -> bool:
            return True

        def get_query(self) -> Any:
            q = super().get_query()
            if has_status and hasattr(self.model, "status"):
                return q.filter(self.model.status == "pending")
            if hasattr(self.model, "approved_by"):
                col = self.model.approved_by
                return q.filter((col.is_(None)) | (col == ""))
            return q

    class ApprovedAdmin(ScenarioAdmin):
        def is_visible(self) -> bool:
            return True

        def get_query(self) -> Any:
            q = super().get_query()
            if has_status and hasattr(self.model, "status"):
                return q.filter(self.model.status == "approved")
            if hasattr(self.model, "approved_by"):
                col = self.model.approved_by
                return q.filter((col.isnot(None)) & (col != ""))
            return q

        def get_count_query(self) -> Any:
            q = super().get_count_query()
            if has_status and hasattr(self.model, "status"):
                return q.filter(self.model.status == "approved")
            if hasattr(self.model, "approved_by"):
                col = self.model.approved_by
                return q.filter((col.isnot(None)) & (col != ""))
            return q

        

    admin = Admin(app, name="Tatlam Admin", template_mode="bootstrap4", index_view=SecureIndex())
    try:
        Scenarios = getattr(Base.classes, table_name)
        admin.add_view(PendingAdmin(Scenarios, session, name="Pending", endpoint="pending"))
        admin.add_view(ApprovedAdmin(Scenarios, session, name="Approved", endpoint="approved"))
        admin.add_view(ScenarioAdmin(Scenarios, session, name="All", endpoint="scenarios"))
    except Exception as e:
        app.logger.warning(
            "[ADMIN] failed to reflect table %s: %s. ensure DB exists; 'status' is optional",
            table_name,
            e,
        )
    return admin


__all__ = ["init_admin"]
