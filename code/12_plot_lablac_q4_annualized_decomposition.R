# Annualized country decomposition for the LATAM paper.
#
# Chart contract:
# - Question: how do education composition and within-group income changes
#   contribute to annualized synthetic mean income growth across countries?
# - Takeaway: nine economies combine a positive education contribution with
#   a negative within-group contribution.
# - Form: sorted horizontal divergent stacked bars with a total-growth marker.
# - Unit: percentage points per year; black diamonds show the CAGR.
# - Palette: teal and orange, with distinct lightness and a neutral marker.
# - Outputs: vector PDF for LaTeX and PNG for visual QA.

suppressPackageStartupMessages(library(ggplot2))

input_path <- file.path(
  "data",
  "processed",
  "lablac_q4_decomposition",
  "country_decompositions.csv"
)
output_dir <- "figures"
qa_dir <- "build"
pdf_path <- file.path(
  output_dir,
  "latam_annualized_decomposition.pdf"
)
png_path <- file.path(
  qa_dir,
  "latam_annualized_decomposition.png"
)

countries <- read.csv(
  input_path,
  stringsAsFactors = FALSE,
  check.names = FALSE
)

required_columns <- c(
  "country",
  "same_source",
  "annualized_growth_synthetic_percent",
  "annualized_education_contribution_percentage_points",
  "annualized_within_contribution_percentage_points"
)
missing_columns <- setdiff(required_columns, names(countries))
if (length(missing_columns) > 0) {
  stop(
    paste(
      "Missing required columns:",
      paste(missing_columns, collapse = ", ")
    )
  )
}
if (nrow(countries) != 14) {
  stop("Expected 14 country rows")
}
if (any(!is.finite(as.matrix(countries[required_columns[-c(1, 2)]])))) {
  stop("Annualized chart data contain non-finite values")
}

identity_error <- max(abs(
  countries$annualized_growth_synthetic_percent
    - countries$annualized_education_contribution_percentage_points
    - countries$annualized_within_contribution_percentage_points
))
if (identity_error > 1e-9) {
  stop("Annualized contributions do not add to total growth")
}

countries$country_label <- ifelse(
  countries$same_source,
  countries$country,
  paste0(countries$country, "*")
)
ordered_labels <- countries$country_label[
  order(countries$annualized_growth_synthetic_percent)
]
countries$country_label <- factor(
  countries$country_label,
  levels = ordered_labels
)
countries$total_label <- sprintf(
  "%.1f",
  countries$annualized_growth_synthetic_percent
)
countries$total_label[
  abs(countries$annualized_growth_synthetic_percent) < 0.05
] <- "0.0"
countries$total_hjust <- ifelse(
  countries$annualized_growth_synthetic_percent >= 0,
  -0.45,
  1.45
)

components <- rbind(
  data.frame(
    country_label = countries$country_label,
    component = "Education composition",
    contribution = (
      countries$annualized_education_contribution_percentage_points
    )
  ),
  data.frame(
    country_label = countries$country_label,
    component = "Within education groups",
    contribution = (
      countries$annualized_within_contribution_percentage_points
    )
  )
)
components$component <- factor(
  components$component,
  levels = c(
    "Education composition",
    "Within education groups"
  )
)

palette <- c(
  "Education composition" = "#2A7F78",
  "Within education groups" = "#D58A45"
)

plot <- ggplot(
  components,
  aes(
    x = country_label,
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
    width = 0.68,
    position = "stack",
    color = "white",
    linewidth = 0.18
  ) +
  geom_point(
    data = countries,
    aes(
      x = country_label,
      y = annualized_growth_synthetic_percent,
      shape = "Total growth (CAGR)"
    ),
    inherit.aes = FALSE,
    size = 2.4,
    stroke = 0.45,
    fill = "#202020",
    color = "#202020"
  ) +
  geom_text(
    data = countries,
    aes(
      x = country_label,
      y = annualized_growth_synthetic_percent,
      label = total_label,
      hjust = total_hjust
    ),
    inherit.aes = FALSE,
    family = "serif",
    size = 2.7,
    color = "#202020"
  ) +
  coord_flip(clip = "off") +
  scale_fill_manual(values = palette) +
  scale_shape_manual(values = c("Total growth (CAGR)" = 23)) +
  scale_y_continuous(
    breaks = seq(-5, 4, by = 1),
    labels = function(x) format(x, trim = TRUE, scientific = FALSE),
    limits = c(-5.6, 4.2),
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
      size = 8.5
    ),
    axis.text.x = element_text(color = "#444444"),
    axis.title.x = element_text(
      color = "#202020",
      margin = margin(t = 8)
    ),
    legend.position = "top",
    legend.justification = "left",
    legend.key.width = grid::unit(1.1, "cm"),
    legend.margin = margin(b = 2),
    plot.margin = margin(6, 18, 10, 8)
  ) +
  guides(
    fill = guide_legend(
      order = 1,
      nrow = 1,
      byrow = TRUE,
      override.aes = list(color = NA)
    ),
    shape = guide_legend(
      order = 2,
      override.aes = list(
        fill = "#202020",
        color = "#202020",
        size = 2.4
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
  height = 6.6,
  units = "in"
)
ggsave(
  png_path,
  plot = plot,
  device = "png",
  width = 7.2,
  height = 6.6,
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