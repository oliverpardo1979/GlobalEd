# Common-window aggregate decomposition for the LATAM paper.
#
# Chart contract:
# - Question: how do economy composition, educational upgrading, and
#   within-group income changes contribute to annualized aggregate growth?
# - Takeaway: educational upgrading raises aggregate income, but declining
#   income within education groups more than offsets that contribution.
# - Form: horizontal divergent stacked bars with a total-growth marker.
# - Unit: percentage points per year; black diamonds show the CAGR.
# - Palette: blue, teal, and orange, with a neutral total marker.
# - Outputs: vector PDF for LaTeX and PNG for visual QA.

suppressPackageStartupMessages(library(ggplot2))

input_path <- file.path(
  "data",
  "processed",
  "lablac_q4_regional_decomposition",
  "regional_decompositions.csv"
)
output_dir <- "figures"
qa_dir <- "build"
pdf_path <- file.path(
  output_dir,
  "latam_regional_annualized_decomposition.pdf"
)
png_path <- file.path(
  qa_dir,
  "latam_regional_annualized_decomposition.png"
)

aggregates <- read.csv(
  input_path,
  stringsAsFactors = FALSE,
  check.names = FALSE
)

required_columns <- c(
  "aggregation",
  "aggregation_label",
  "annualized_growth_percent",
  "annualized_country_composition_percentage_points",
  "annualized_education_contribution_percentage_points",
  "annualized_within_contribution_percentage_points"
)
missing_columns <- setdiff(required_columns, names(aggregates))
if (length(missing_columns) > 0) {
  stop(
    paste(
      "Missing required columns:",
      paste(missing_columns, collapse = ", ")
    )
  )
}
if (nrow(aggregates) != 3) {
  stop("Expected three aggregation methods")
}
numeric_columns <- required_columns[-c(1, 2)]
if (any(!is.finite(as.matrix(aggregates[numeric_columns])))) {
  stop("Regional chart data contain non-finite values")
}

identity_error <- max(abs(
  aggregates$annualized_growth_percent
    - aggregates$annualized_country_composition_percentage_points
    - aggregates$annualized_education_contribution_percentage_points
    - aggregates$annualized_within_contribution_percentage_points
))
if (identity_error > 1e-9) {
  stop("Annualized contributions do not add to total growth")
}

label_order <- c(
  "Equal weights by economy",
  "Observed employment weights",
  "Fixed employment weights"
)
aggregates$aggregation_label <- factor(
  aggregates$aggregation_label,
  levels = label_order
)
aggregates$total_label <- sprintf(
  "%.2f",
  aggregates$annualized_growth_percent
)
aggregates$total_hjust <- ifelse(
  aggregates$annualized_growth_percent >= 0,
  -0.45,
  1.45
)

components <- rbind(
  data.frame(
    aggregation_label = aggregates$aggregation_label,
    component = "Economy composition",
    contribution = (
      aggregates$annualized_country_composition_percentage_points
    )
  ),
  data.frame(
    aggregation_label = aggregates$aggregation_label,
    component = "Education composition",
    contribution = (
      aggregates$annualized_education_contribution_percentage_points
    )
  ),
  data.frame(
    aggregation_label = aggregates$aggregation_label,
    component = "Within education groups",
    contribution = (
      aggregates$annualized_within_contribution_percentage_points
    )
  )
)
components$component <- factor(
  components$component,
  levels = c(
    "Economy composition",
    "Education composition",
    "Within education groups"
  )
)

palette <- c(
  "Economy composition" = "#4C78A8",
  "Education composition" = "#2A7F78",
  "Within education groups" = "#D58A45"
)

plot <- ggplot(
  components,
  aes(
    x = aggregation_label,
    y = contribution,
    fill = component
  )
) +
  geom_hline(
    yintercept = 0,
    color = "#333333",
    linewidth = 0.45
  ) +
  geom_col(
    width = 0.62,
    position = "stack",
    color = "white",
    linewidth = 0.18
  ) +
  geom_point(
    data = aggregates,
    aes(
      x = aggregation_label,
      y = annualized_growth_percent,
      shape = "Total growth (CAGR)"
    ),
    inherit.aes = FALSE,
    size = 2.6,
    stroke = 0.45,
    fill = "#202020",
    color = "#202020"
  ) +
  geom_text(
    data = aggregates,
    aes(
      x = aggregation_label,
      y = annualized_growth_percent,
      label = total_label,
      hjust = total_hjust
    ),
    inherit.aes = FALSE,
    family = "serif",
    size = 3.0,
    color = "#202020"
  ) +
  coord_flip(clip = "off") +
  scale_fill_manual(values = palette) +
  scale_shape_manual(values = c("Total growth (CAGR)" = 23)) +
  scale_y_continuous(
    breaks = seq(-2.5, 1.5, by = 0.5),
    labels = function(x) format(x, trim = TRUE, scientific = FALSE),
    limits = c(-2.55, 1.55),
    expand = expansion(mult = c(0, 0))
  ) +
  labs(
    x = NULL,
    y = "Contribution to annualized growth (percentage points per year)",
    fill = NULL,
    shape = NULL
  ) +
  theme_minimal(base_family = "serif", base_size = 9.5) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(
      color = "#DDDDDD",
      linewidth = 0.35
    ),
    axis.text.y = element_text(
      color = "#202020",
      size = 8.8
    ),
    axis.text.x = element_text(color = "#444444"),
    axis.title.x = element_text(
      color = "#202020",
      margin = margin(t = 8)
    ),
    legend.position = "top",
    legend.justification = "left",
    legend.key.width = grid::unit(0.85, "cm"),
    legend.margin = margin(b = 2),
    plot.margin = margin(6, 18, 10, 8)
  ) +
  guides(
    fill = guide_legend(
      order = 1,
      nrow = 2,
      byrow = TRUE,
      override.aes = list(color = NA)
    ),
    shape = guide_legend(
      order = 2,
      override.aes = list(
        fill = "#202020",
        color = "#202020",
        size = 2.6
      )
    )
  )

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(qa_dir, recursive = TRUE, showWarnings = FALSE)
ggsave(
  pdf_path,
  plot = plot,
  device = "pdf",
  version = "1.5",
  family = "Times",
  width = 7.2,
  height = 3.6,
  units = "in"
)
ggsave(
  png_path,
  plot = plot,
  device = "png",
  width = 7.2,
  height = 3.6,
  units = "in",
  dpi = 220,
  bg = "white"
)

message(
  sprintf(
    "Wrote %s and %s; maximum identity error %.3e",
    pdf_path,
    png_path,
    identity_error
  )
)
