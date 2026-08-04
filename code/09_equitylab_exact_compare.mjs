import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const attachedPath = process.argv[2];
if (!attachedPath) {
  throw new Error(
    "Usage: node code/09_equitylab_exact_compare.mjs path/to/EquityLAB.xlsx",
  );
}

const inputPaths = {
  attached: attachedPath,
  wage: path.resolve(
    "data/raw/world_bank_lablac/Wage-tableau.xlsx",
  ),
};

function normalize(value) {
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "number") return Number(value.toPrecision(15));
  return value ?? null;
}

function key(values) {
  return JSON.stringify(values.map(normalize));
}

async function readFirstSheet(filePath) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  const sheet = workbook.worksheets.getItemAt(0);
  return sheet.getUsedRange(true).values;
}

const attached = await readFirstSheet(inputPaths.attached);
const wage = await readFirstSheet(inputPaths.wage);
const attachedRows = attached.slice(1);
const wageHeader = wage[0];
const column = Object.fromEntries(wageHeader.map((name, index) => [name, index]));

const wageGrouped = new Map();
for (const row of wage.slice(1)) {
  const dimensions = [
    row[column.Pais],
    row[column.Period],
    row[column.Indicator_ESP],
    row[column.Category_ESP],
  ];
  const dimensionKey = key(dimensions);
  const value = normalize(row[column.Value]);
  if (
    typeof value === "number" &&
    (!wageGrouped.has(dimensionKey) || value > wageGrouped.get(dimensionKey))
  ) {
    wageGrouped.set(dimensionKey, value);
  }
}

const projectedWageRows = [...wageGrouped.entries()].map(([dimensionKey, value]) => [
  ...JSON.parse(dimensionKey),
  value,
]);
const attachedSet = new Set(attachedRows.map(key));
const wageSet = new Set(projectedWageRows.map(key));
const onlyAttached = [...attachedSet].filter((row) => !wageSet.has(row));
const onlyWage = [...wageSet].filter((row) => !attachedSet.has(row));

const report = {
  attachedRows: attachedRows.length,
  attachedUniqueRows: attachedSet.size,
  projectedWageRows: projectedWageRows.length,
  projectedWageUniqueRows: wageSet.size,
  exactSetMatch: onlyAttached.length === 0 && onlyWage.length === 0,
  onlyAttachedCount: onlyAttached.length,
  onlyWageCount: onlyWage.length,
  onlyAttachedSample: onlyAttached.slice(0, 10).map(JSON.parse),
  onlyWageSample: onlyWage.slice(0, 10).map(JSON.parse),
};

const outputDir = path.resolve(".tmp/equitylab_audit");
await fs.mkdir(outputDir, {
  recursive: true,
});
await fs.writeFile(
  path.join(outputDir, "exact_compare.json"),
  JSON.stringify(report, null, 2),
);
console.log(JSON.stringify(report, null, 2));
