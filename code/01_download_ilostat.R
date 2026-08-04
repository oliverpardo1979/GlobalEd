#!/usr/bin/env Rscript

# Download the matched annual ILOSTAT tables used by the global paper.
#
# Population: employees.
# Outcome: average monthly earnings by educational attainment.
# Weights: employment by status in employment and educational attainment,
# restricted downstream to employees.

suppressPackageStartupMessages(library(Rilostat))

command <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", command[grep("^--file=", command)])
root <- normalizePath(file.path(dirname(script), ".."))
raw_dir <- file.path(root, "data", "raw", "ilostat")
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)

tables <- c(
  earnings = "EAR_EMTA_SEX_EDU_NB_A",
  employment = "EMP_TEMP_SEX_STE_EDU_NB_A"
)

for (name in names(tables)) {
  id <- tables[[name]]
  message("Downloading ", id)
  data <- get_ilostat(
    id = id,
    segment = "indicator",
    type = "both",
    time_format = "raw",
    cache = FALSE,
    quiet = TRUE
  )
  output <- file.path(raw_dir, paste0(id, ".csv.gz"))
  write.csv(data, gzfile(output), row.names = FALSE, na = "")
  message("Saved ", nrow(data), " rows to ", output)
}
