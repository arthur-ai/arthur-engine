mod utils;

use std::io::Cursor;

use csv::{ReaderBuilder, WriterBuilder};
use js_sys::Uint32Array;
use serde_json::{Map, Value};
use wasm_bindgen::prelude::*;

// ---------------------------------------------------------------------------
// sort_rows
// ---------------------------------------------------------------------------

/// Sort rows by a pre-extracted column and return sorted indices.
///
/// `values_json` is a JSON-encoded `Array<string | null>` — one entry per row,
/// the already-extracted value for the sort column (`null` means the column is
/// absent for that row).
///
/// Returns a `Uint32Array` of row indices in sorted order. The caller reorders
/// its original row array using these indices, which eliminates the O(N × M)
/// `Array.find` inside every comparator call.
///
/// Sort heuristic mirrors the TypeScript implementation:
/// - If every non-null value parses as a finite f64, sort numerically.
/// - Otherwise sort lexicographically (byte order, same as ASCII `localeCompare`
///   for the ASCII-only strings that dataset column values typically are).
/// - Null values always sort last, regardless of direction.
#[wasm_bindgen]
pub fn sort_rows(values_json: &str, ascending: bool) -> Result<Uint32Array, JsError> {
    utils::set_panic_hook();

    let values: Vec<Option<String>> =
        serde_json::from_str(values_json).map_err(|e| JsError::new(&e.to_string()))?;

    let n = values.len();

    // Determine whether every non-null value is numeric.
    let all_numeric = values.iter().all(|v| match v {
        None => true,
        Some(s) => s.parse::<f64>().map(|f| f.is_finite()).unwrap_or(false),
    });

    let mut indices: Vec<u32> = (0..n as u32).collect();

    if all_numeric {
        indices.sort_unstable_by(|&a, &b| {
            let av = values[a as usize].as_deref().and_then(|s| s.parse::<f64>().ok());
            let bv = values[b as usize].as_deref().and_then(|s| s.parse::<f64>().ok());
            match (av, bv) {
                (None, None) => std::cmp::Ordering::Equal,
                (None, Some(_)) => std::cmp::Ordering::Greater,
                (Some(_), None) => std::cmp::Ordering::Less,
                (Some(a), Some(b)) => {
                    let ord = a.partial_cmp(&b).unwrap_or(std::cmp::Ordering::Equal);
                    if ascending { ord } else { ord.reverse() }
                }
            }
        });
    } else {
        indices.sort_unstable_by(|&a, &b| {
            let av = values[a as usize].as_deref();
            let bv = values[b as usize].as_deref();
            match (av, bv) {
                (None, None) => std::cmp::Ordering::Equal,
                (None, Some(_)) => std::cmp::Ordering::Greater,
                (Some(_), None) => std::cmp::Ordering::Less,
                (Some(a), Some(b)) => {
                    let ord = a.cmp(b);
                    if ascending { ord } else { ord.reverse() }
                }
            }
        });
    }

    let array = Uint32Array::new_with_length(n as u32);
    for (i, &idx) in indices.iter().enumerate() {
        array.set_index(i as u32, idx);
    }
    Ok(array)
}

// ---------------------------------------------------------------------------
// serialize_csv
// ---------------------------------------------------------------------------

/// Serialize an array of row objects to a CSV string.
///
/// `rows_json` is a JSON-encoded `Array<Record<string, string>>`. The header
/// row is derived from the keys of the first object; all subsequent rows must
/// have the same key set (matching the behaviour of `Papa.unparse`).
///
/// Returns the complete CSV string including the header row.
#[wasm_bindgen]
pub fn serialize_csv(rows_json: &str) -> Result<String, JsError> {
    utils::set_panic_hook();

    let rows: Vec<Map<String, Value>> =
        serde_json::from_str(rows_json).map_err(|e| JsError::new(&e.to_string()))?;

    if rows.is_empty() {
        return Ok(String::new());
    }

    let headers: Vec<&str> = rows[0].keys().map(|k| k.as_str()).collect();

    let mut out = Vec::new();
    {
        let mut wtr = WriterBuilder::new()
            .has_headers(true)
            .from_writer(&mut out);

        wtr.write_record(&headers)
            .map_err(|e| JsError::new(&e.to_string()))?;

        for row in &rows {
            let record: Vec<&str> = headers
                .iter()
                .map(|h| match row.get(*h) {
                    Some(Value::String(s)) => s.as_str(),
                    _ => "",
                })
                .collect();
            wtr.write_record(&record)
                .map_err(|e| JsError::new(&e.to_string()))?;
        }

        wtr.flush().map_err(|e| JsError::new(&e.to_string()))?;
    }

    String::from_utf8(out).map_err(|e| JsError::new(&e.to_string()))
}

// ---------------------------------------------------------------------------
// parse_csv
// ---------------------------------------------------------------------------

/// Parse a CSV string and return JSON-encoded `{ columns: string[], rows: Array<Record<string, string>> }`.
///
/// `delimiter` must be a single ASCII character passed as a one-character string
/// (e.g. `","`, `";"`, `"\t"`, `"|"`). Defaults to `","` if the string is empty
/// or longer than one byte.
#[wasm_bindgen]
pub fn parse_csv(input: &str, has_header: bool, delimiter: &str) -> Result<String, JsError> {
    utils::set_panic_hook();

    let delim_byte = delimiter.bytes().next().unwrap_or(b',');

    let mut rdr = ReaderBuilder::new()
        .has_headers(has_header)
        .delimiter(delim_byte)
        .flexible(true)
        .from_reader(Cursor::new(input.as_bytes()));

    let columns: Vec<String> = if has_header {
        rdr.headers()
            .map_err(|e| JsError::new(&e.to_string()))?
            .iter()
            .map(|s| s.to_owned())
            .collect()
    } else {
        Vec::new()
    };

    let mut rows: Vec<Map<String, Value>> = Vec::new();

    for result in rdr.records() {
        let record = result.map_err(|e| JsError::new(&e.to_string()))?;

        if has_header {
            let mut obj = Map::new();
            for (col, val) in columns.iter().zip(record.iter()) {
                obj.insert(col.clone(), Value::String(val.to_owned()));
            }
            rows.push(obj);
        } else {
            // No header: use "0", "1", ... as synthetic column names.
            let mut obj = Map::new();
            for (i, val) in record.iter().enumerate() {
                obj.insert(i.to_string(), Value::String(val.to_owned()));
            }
            rows.push(obj);
        }
    }

    let output = serde_json::json!({
        "columns": columns,
        "rows": rows,
    });

    serde_json::to_string(&output).map_err(|e| JsError::new(&e.to_string()))
}

// ---------------------------------------------------------------------------
// detect_delimiter
// ---------------------------------------------------------------------------

/// Detect the most likely CSV delimiter from a preview string.
///
/// Tries `[',', ';', '\t', '|']`, parses each with the `csv` crate, computes
/// per-delimiter column-count mean and variance, scores as `mean / (std_dev + 1.0)`.
/// Returns the highest-scoring delimiter as a string, defaulting to `","`.
#[wasm_bindgen]
pub fn detect_delimiter(preview: &str) -> String {
    utils::set_panic_hook();

    const CANDIDATES: &[u8] = &[b',', b';', b'\t', b'|'];

    let best = CANDIDATES
        .iter()
        .filter_map(|&delim| {
            let score = score_delimiter(preview, delim)?;
            Some((delim, score))
        })
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

    match best {
        Some((delim, score)) if score > 0.0 => {
            String::from_utf8(vec![delim]).unwrap_or_else(|_| ",".to_owned())
        }
        _ => ",".to_owned(),
    }
}

/// Returns `None` if parsing produces no rows or every row has ≤ 1 column
/// (indistinguishable from no-delimiter case).
fn score_delimiter(preview: &str, delim: u8) -> Option<f64> {
    let mut rdr = ReaderBuilder::new()
        .has_headers(false)
        .delimiter(delim)
        .flexible(true)
        .from_reader(Cursor::new(preview.as_bytes()));

    let col_counts: Vec<f64> = rdr
        .records()
        .filter_map(|r| r.ok())
        .map(|r| r.len() as f64)
        .collect();

    if col_counts.is_empty() {
        return None;
    }

    let mean = col_counts.iter().sum::<f64>() / col_counts.len() as f64;
    if mean <= 1.0 {
        return None;
    }

    let variance = col_counts
        .iter()
        .map(|&c| (c - mean).powi(2))
        .sum::<f64>()
        / col_counts.len() as f64;
    let std_dev = variance.sqrt();

    Some(mean / (std_dev + 1.0))
}
