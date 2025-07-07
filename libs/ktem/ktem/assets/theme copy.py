from typing import Iterable

from gradio.themes import Soft
from gradio.themes.utils import colors, fonts, sizes

gray = colors.Color(
    name="dark",
    c50="#f9fafb",
    c100="#edeef0",
    c200="#e1e2e6",
    c300="#d5d6dd",
    c400="#cacbd5",
    c500="#acadb7",
    c600="#313138",
    c700="#25252b",
    c800="#19191e",
    c900="#0d0d11",
    c950="#010104",
)

err_txt = "#f05656"
gradient = "linear-gradient(90deg, *primary_400 20%, *secondary_500 80%)"
gradient_muted = "linear-gradient(90deg, *primary_500 20%, *secondary_600 80%)"

err_dark = "rgba(228, 98, 98, 1)"
err_dark_muted = "rgba(228, 98, 98, 0.75)"

err = "rgba(255, 93, 93, 1)"
err_muted = "rgba(237, 80, 80, 1)"


docu_background_primary = "#F9F9FD"  # Soft white background
docu_background_secondary = "#F1F6FE"  # Soft white background

docu_primary = "#2F80ED"  # Call to action color
docu_secondary = "#E8F0FE"  # Call to action color

docu_primary_hover = "#5899F1"  # Call to action color
docu_secondary_hover = "#D1E2FC"  # secondary hover

docu_text_primary = "#1A1A1A"  # Primary text color
docu_text_secondary = "#5C667B"  # secondary text color

docu_success = "#27AE60"  # success color
docu_warning = "#F2C94C"  # warning color

common = dict(
    # element colours
    color_accent="*primary_400",
    # shadows
    shadow_drop="0 0px 5px 1px rgb(0 0 0 / 0.05)",
    shadow_drop_lg="0 0 10px 3px rgba(0 0 0 / 0.06)",
    # layout atoms
    block_label_margin="*spacing_xl",
    block_label_padding="*spacing_xl",
    block_label_shadow="none",
    layout_gap="*spacing_xxl",
    section_header_text_size="*text_lg",
    # buttons
    button_shadow="none",
    button_shadow_active="*shadow_drop",
    button_shadow_hover="none",
    # Custom colors based on user requirements
    body_text_color="docu_primary",  # Primary text color
    body_text_color_subdued="docu_text_secondary",  # Secondary text color
   # High contrast black text
    block_label_text_color="*primary_600",
        # Light panels, accents
    input_background_fill="#2F80ED",
    # Success and warning
    # stat_background_fill_success="#27AF60",  # Green for completion
    # error_background_fill_warning="#F2C94C", # Yellow for warnings
    # -----
)
dark_mode = dict(
    # body attributes
    body_text_color_subdued_dark="*neutral_300",
    # element colours
    background_fill_secondary_dark="*neutral_950",
    border_color_accent_dark="rgba(255,255,255,0)",
    border_color_primary_dark="*neutral_600",
    color_accent_soft_dark="*secondary_400",
    # text
    link_text_color_dark="*secondary_200",
    link_text_color_active_dark="*secondary_300",
    link_text_color_visited_dark="*secondary_400",
    # layout atoms
    block_label_background_fill_dark="*neutral_800",
    block_label_border_width_dark="0px",
    block_label_text_color_dark="*primary_200",
    block_shadow_dark="none",
    block_title_text_color_dark="*primary_200",
    panel_border_width_dark="0px",
    # component atoms
    checkbox_background_color_selected_dark="*primary_400",
    checkbox_border_color_focus_dark="*primary_400",
    checkbox_border_color_selected_dark="*primary_500",
    checkbox_label_background_fill_selected_dark="*primary_200",
    checkbox_label_text_color_selected_dark="*neutral_700",
    error_border_color_dark=err_dark,
    error_text_color_dark="*neutral_100",
    error_icon_color_dark=err_dark,
    input_background_fill_dark="*neutral_600",
    input_border_color_dark="*input_background_fill",
    input_border_color_focus_dark="*input_background_fill",
    input_placeholder_color_dark="*neutral_500",
    loader_color_dark="*primary_200",
    slider_color_dark="*primary_300",
    stat_background_fill_dark="*secondary_100",
    table_border_color_dark="*neutral_800",
    table_even_background_fill_dark="*neutral_900",
    table_odd_background_fill_dark="*neutral_800",
    table_row_focus_dark="*neutral_600",
    # buttons
    button_primary_background_fill_dark=gradient,
    button_primary_background_fill_hover_dark=gradient_muted,
    button_secondary_background_fill_hover_dark="*neutral_700",
    button_cancel_background_fill_dark=err_dark,
    button_cancel_background_fill_hover_dark=err_dark_muted,
)

light_mode = dict(
    background_fill_primary="docu_background_primary",
    background_fill_secondary="docu_background_secondary",
    # body attributes
    body_background_fill="docu_background_primary",
    # body_text_color_subdued="*neutral_600",
    border_color_accent="rgba(255,255,255,0)",
    border_color_primary="*neutral_300",
    color_accent_soft="docu_secondary", 
    # text
    link_text_color="*secondary_400",
    link_text_color_visited="*secondary_700",
    # layout atoms
    block_label_border_width="0px",
    block_label_background_fill="white",
    block_label_text_color="docu_primary",
    block_shadow="none",
    block_title_text_color="none",
    panel_border_width="0px",
    # component atoms
    checkbox_background_color_selected="*primary_400",
    checkbox_border_color_focus="*primary_400",
    checkbox_border_color_selected="*primary_400",
    checkbox_label_border_color="*primary_200",
    error_background_fill="*background_fill_primary",
    error_border_color=err_muted,
    error_text_color="*neutral_800",
    # input_background_fill="*neutral_200",
    input_border_color="*input_background_fill",
    input_border_color_focus="*input_background_fill",
    input_placeholder_color="*neutral_500",
    loader_color="*primary_300",
    slider_color="*primary_400",
    stat_background_fill="*secondary_300",
    table_even_background_fill="docu_background_secondary",
    table_odd_background_fill="*neutral_300",
    table_row_focus="*secondary_200",
    # buttons
    button_primary_background_fill=docu_primary,
    button_primary_background_fill_hover=docu_primary_hover,
    button_secondary_background_fill=docu_secondary,
    button_secondary_background_fill_hover=docu_secondary_hover,
    button_cancel_background_fill=err_muted,
    button_cancel_background_fill_hover=err,
    button_cancel_text_color="*neutral_50",
)

# Custom color palette based on user requirements
custom_colors = colors.Color(
    name="custom_blue",
    c50="#F9FEFF",      # Very light blue
    c100="#E8F6FF",     # Light blue
    c200="#D1EDFF",     # Lighter blue
    c300="#A9DDFF",     # Light blue
    c400="#2F80ED",     # Primary Blue (#2F80ED - CTA, highlights)
    c500="#1E6FDB",     # Medium blue
    c600="#1A5DB3",     # Darker blue
    c700="#144B8A",     # Dark blue
    c800="#0E3A61",     # Very dark blue
    c900="#082838",     # Almost black blue
    c950="#041419",     # Darkest blue
)

# Background and neutral colors
neutral_colors = colors.Color(
    name="neutral_custom",
    c50="#F9F9FD",      # Soft white (#F9F9FD - Background)
    c100="#8CB8F6",     # Very light grey  #1st panel dataframe, secondary hover button
    c200="#E1E2E6",     # Light grey (current selection)
    c300="#E8F0FE",     # Medium light grey #2nd panel dataframe, secondary button  
    c400="#202020",     # Medium grey
    c500="#202020",     # Medium dark grey
    c600="#1A1A1A",     # Secondary text (#5C667B - For file meta, timestamps)
    c700="#1A1A1A",     # Primary text (#1A1A1A - High contrast black)
    c800="#19191E",     # Very dark grey
    c900="#0D0D11",     # Almost black
    c950="#010104",     # Pure black
)

# Success and warning colors
success_color = "#27AF60"  # Green tags, completion states
warning_color = "#F2C94C"  # For flagged risks

# Secondary blue for accents
secondary_blue = "#E8F0FE"  # Light panels, accents


class Kotaemon(Soft):
    """
    Official theme of Kotaemon.
    Public version: https://huggingface.co/spaces/lone17/kotaemon
    """

    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = custom_colors,      # Changed to custom blue
        secondary_hue: colors.Color | str = colors.blue,
        neutral_hue: colors.Color | str = neutral_colors,     # Changed to custom neutral
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Quicksand"),
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("IBM Plex Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        self.name = "kotaemon"
        # Set default theme mode to light
        super().set(
            # **common,
            # **dark_mode,
            **light_mode,
        )
        
    @property 
    def default_mode(self):
        """Return the default theme mode"""
        return "light"
