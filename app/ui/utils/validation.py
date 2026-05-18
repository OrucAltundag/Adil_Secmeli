# -*- coding: utf-8 -*-
"""UI form validation utilities for user input."""

from tkinter import messagebox
from typing import Callable, Any


class FormValidationError(Exception):
    """Raised when form validation fails."""
    pass


def validate_combobox_selection(
    combobox,
    field_name: str,
    error_title: str = "Eksik Alan",
) -> bool:
    """
    Validate that a combobox has a value selected.
    
    Args:
        combobox: ttk.Combobox widget to validate
        field_name: Display name for the field (Turkish)
        error_title: Title for error messagebox
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        Displays messagebox with error
    """
    value = combobox.get() if combobox else ""
    if not value or not value.strip():
        messagebox.showerror(
            error_title,
            f"{field_name} seçilmelidir.",
        )
        combobox.focus() if combobox else None
        return False
    return True


def validate_required_field(
    widget,
    field_name: str,
    error_title: str = "Eksik Alan",
) -> bool:
    """
    Validate that a widget has a non-empty value.
    
    Args:
        widget: Tkinter widget (Entry, Text, etc.)
        field_name: Display name for the field (Turkish)
        error_title: Title for error messagebox
        
    Returns:
        True if valid, False otherwise
    """
    if hasattr(widget, "get"):
        value = widget.get()
    else:
        value = ""
    
    if not value or not value.strip():
        messagebox.showerror(
            error_title,
            f"{field_name} boş bırakılamaz.",
        )
        widget.focus() if widget else None
        return False
    return True


def validate_form(
    fields: dict[str, tuple[Any, str, Callable[[Any], bool]]],
    error_title: str = "Form Hatası",
) -> bool:
    """
    Validate multiple form fields.
    
    Args:
        fields: Dict of field_name -> (widget, display_name, validator_func)
                Each validator_func should return True if valid, False otherwise
        error_title: Title for error messagebox
        
    Returns:
        True if all fields are valid, False otherwise
        
    Example:
        validate_form({
            "year": (year_entry, "Yıl", lambda w: int(w.get()) >= 2000),
            "faculty": (faculty_combo, "Fakülte", lambda w: bool(w.get())),
        })
    """
    for field_name, (widget, display_name, validator_func) in fields.items():
        try:
            if not validator_func(widget):
                widget.focus() if widget else None
                return False
        except Exception as e:
            messagebox.showerror(
                error_title,
                f"{display_name} doğrulaması başarısız: {str(e)}",
            )
            widget.focus() if widget else None
            return False
    return True


def disable_button_until_valid(
    button,
    validators: list[Callable[[], bool]],
    check_interval_ms: int = 500,
) -> None:
    """
    Disable a button until all validators return True.
    Check validators periodically and update button state.
    
    Args:
        button: tk.Button widget to control
        validators: List of validator functions (each returns bool)
        check_interval_ms: How often to check validators (milliseconds)
    """
    def check_validity():
        all_valid = all(validator() for validator in validators)
        button.config(state="normal" if all_valid else "disabled")
        button.after(check_interval_ms, check_validity)
    
    check_validity()


def show_validation_error(
    message: str,
    title: str = "Hata",
    details: str = "",
) -> None:
    """
    Show a user-friendly validation error messagebox.
    
    Args:
        message: Main error message (Turkish)
        title: Messagebox title
        details: Optional detailed information
    """
    full_message = message
    if details:
        full_message += f"\n\nDetaylar:\n{details}"
    messagebox.showerror(title, full_message)


def show_validation_warning(
    message: str,
    title: str = "Uyarı",
) -> None:
    """
    Show a user-friendly validation warning messagebox.
    
    Args:
        message: Warning message (Turkish)
        title: Messagebox title
    """
    messagebox.showwarning(title, message)


def show_validation_info(
    message: str,
    title: str = "Bilgi",
) -> None:
    """
    Show a user-friendly validation info messagebox.
    
    Args:
        message: Info message (Turkish)
        title: Messagebox title
    """
    messagebox.showinfo(title, message)
