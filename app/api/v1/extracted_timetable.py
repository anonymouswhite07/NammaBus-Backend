import io
import os
import zipfile
import json
import uuid
import re
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import RoleChecker
from app.repositories.all_repositories import extracted_timetable_repo
from app.schemas.all_schemas import StandardResponse, ExtractedImportResult, ExtractedTimetableRow

router = APIRouter()
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "exports")

def normalize_time_str(val: str) -> Optional[str]:
    """
    Normalizes time strings from extraction formats:
    - '2.25' or '14.05' -> '02:25' or '14:05'
    - '6:15 PM' -> '18:15'
    - '09.15am' -> '09:15'
    """
    val = val.strip()
    if not val:
        return None
    val_lower = val.lower()
    is_pm = "pm" in val_lower
    is_am = "am" in val_lower
    
    cleaned = val_lower.replace("am", "").replace("pm", "").strip()
    
    # Check if dot/colon separator is present
    if "." in cleaned:
        parts = cleaned.split(".")
    elif ":" in cleaned:
        parts = cleaned.split(":")
    else:
        parts = [cleaned, "00"]
        
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if is_pm and h < 12:
            h += 12
        elif is_am and h == 12:
            h = 0
        return f"{h:02d}:{m:02d}"
    except:
        return None

@router.post("/import", response_model=StandardResponse[ExtractedImportResult])
async def import_extracted_timetable(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """
    Accepts multiple JSON files or a single ZIP file containing JSON files.
    Validates schema, deduplicates, merges, sorts, writes outputs (Excel, CSV, JSON),
    and imports into the database.
    """
    total_processed = 0
    unique_records = []
    seen_keys = set()
    duplicates_count = 0
    
    for upload_file in files:
        contents = await upload_file.read()
        filename = upload_file.filename.lower()
        
        raw_items = []
        if filename.endswith(".json"):
            try:
                json_str = contents.decode("utf-8")
                json_str_repaired = re.sub(r'\\(?!["\\/bfnrt])(?!u[0-9a-fA-F]{4})', r'\\\\', json_str)
                data = json.loads(json_str_repaired)
                if isinstance(data, list):
                    raw_items.extend(data)
                elif isinstance(data, dict):
                    raw_items.append(data)
            except Exception as parse_err:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to parse JSON file '{upload_file.filename}': {parse_err}"
                )
        elif filename.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(contents)) as z:
                    for z_name in z.namelist():
                        if z_name.lower().endswith(".json"):
                            with z.open(z_name) as z_file:
                                z_contents = z_file.read()
                                json_str = z_contents.decode("utf-8")
                                json_str_repaired = re.sub(r'\\(?!["\\/bfnrt])(?!u[0-9a-fA-F]{4})', r'\\\\', json_str)
                                data = json.loads(json_str_repaired)
                                if isinstance(data, list):
                                    raw_items.extend(data)
                                elif isinstance(data, dict):
                                    raw_items.append(data)
            except Exception as zip_err:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process ZIP archive '{upload_file.filename}': {zip_err}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type for file '{upload_file.filename}'. Use .json or .zip."
            )
            
        # Validate schema and deduplicate
        for item in raw_items:
            total_processed += 1
            try:
                validated_row = ExtractedTimetableRow.model_validate(item)
            except Exception as val_err:
                # Skip invalid schema rows or raise HTTP exception
                continue
                
            # Create a unique key for deduplication
            key = (
                validated_row.sector.strip().lower(),
                validated_row.page,
                validated_row.serial_no,
                validated_row.route_code.strip().lower(),
                validated_row.arrival_time.strip().lower(),
                validated_row.departure_time.strip().lower(),
                validated_row.operator.strip().lower(),
                validated_row.destination.strip().lower()
            )
            
            if key in seen_keys:
                duplicates_count += 1
                continue
                
            seen_keys.add(key)
            unique_records.append(validated_row)

    # Sort merged list: sector (alphabetically), page (ascending), serial_no (ascending)
    unique_records.sort(key=lambda r: (r.sector.lower(), r.page, r.serial_no))
    
    # Save the database records and generate outputs
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    # Database mapping data preparation
    db_records = []
    export_data = []
    
    for record in unique_records:
        arr_norm = normalize_time_str(record.arrival_time)
        dep_norm = normalize_time_str(record.departure_time)
        
        db_records.append({
            "sector": record.sector.strip(),
            "page_no": record.page,
            "serial_number": record.serial_no,
            "arrival_time": record.arrival_time.strip(),
            "departure_time": record.departure_time.strip(),
            "arrival_time_normalized": arr_norm,
            "departure_time_normalized": dep_norm,
            "route_code": record.route_code.strip(),
            "operator": record.operator.strip(),
            "destination": record.destination.strip(),
            "remarks": record.remarks.strip() if record.remarks else None,
            "low_confidence": record.low_confidence
        })
        
        # Prepare for CSV/Excel export
        export_data.append({
            "sector": record.sector.strip(),
            "page": record.page,
            "serial_no": record.serial_no,
            "arrival_time": record.arrival_time.strip(),
            "departure_time": record.departure_time.strip(),
            "arrival_time_normalized": arr_norm or "",
            "departure_time_normalized": dep_norm or "",
            "route_code": record.route_code.strip(),
            "operator": record.operator.strip(),
            "destination": record.destination.strip(),
            "remarks": record.remarks or "",
            "low_confidence": record.low_confidence
        })
        
    # Write files to exports directory
    json_path = os.path.join(EXPORTS_DIR, "merged_routes.json")
    xlsx_path = os.path.join(EXPORTS_DIR, "routes.xlsx")
    csv_path = os.path.join(EXPORTS_DIR, "routes.csv")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
        
    df = pd.DataFrame(export_data)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_excel(xlsx_path, index=False)
    
    # Insert new entries into the database (handling DB unique checks)
    saved_count = 0
    for db_rec in db_records:
        # Check if record already exists
        query = select(extracted_timetable_repo.model).filter(
            extracted_timetable_repo.model.sector == db_rec["sector"],
            extracted_timetable_repo.model.page_no == db_rec["page_no"],
            extracted_timetable_repo.model.serial_number == db_rec["serial_number"],
            extracted_timetable_repo.model.arrival_time == db_rec["arrival_time"],
            extracted_timetable_repo.model.departure_time == db_rec["departure_time"],
            extracted_timetable_repo.model.route_code == db_rec["route_code"],
            extracted_timetable_repo.model.operator == db_rec["operator"],
            extracted_timetable_repo.model.destination == db_rec["destination"]
        )
        res = await db.execute(query)
        existing = res.scalars().first()
        
        if not existing:
            await extracted_timetable_repo.create(db, obj_in=db_rec)
            saved_count += 1
            
    await db.commit()
    
    result = ExtractedImportResult(
        total_records_processed=total_processed,
        unique_records_count=len(unique_records),
        duplicates_skipped=duplicates_count,
        saved_to_db_count=saved_count,
        merged_json_url="/api/v1/extracted-timetable/download/merged_routes.json",
        merged_xlsx_url="/api/v1/extracted-timetable/download/routes.xlsx",
        merged_csv_url="/api/v1/extracted-timetable/download/routes.csv"
    )
    
    return StandardResponse(
        success=True,
        message="Timetable files processed, merged, and saved.",
        data=result
    )

@router.get("/download/{filename}")
async def download_merged_file(filename: str):
    """
    Downloads the generated merged CSV, Excel, or JSON files.
    """
    # Safe validation of filename to prevent path traversal
    safe_filenames = {"merged_routes.json", "routes.xlsx", "routes.csv"}
    if filename not in safe_filenames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested file not found or access denied."
        )
        
    filepath = os.path.join(EXPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File has not been generated yet. Please run import first."
        )
        
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream"
    )

@router.post("/publish", response_model=StandardResponse[dict])
async def publish_extracted_timetable(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """
    Processes the raw staging data in extracted_timetables and publishes it
    into the active routes, stops, route_stops, and timetables tables.
    """
    # 1. Retrieve all extracted timetable rows
    query = select(extracted_timetable_repo.model)
    result = await db.execute(query)
    extracted_rows = result.scalars().all()
    
    if not extracted_rows:
        return StandardResponse(
            success=True,
            message="No extracted timetable records found to publish.",
            data={"routes_created": 0, "stops_created": 0, "timetables_created": 0}
        )
        
    # Import repos
    from app.repositories.all_repositories import route_repo, stop_repo, route_stop_repo, timetable_repo
    from datetime import datetime
    from sqlalchemy import and_
    
    routes_created = 0
    stops_created = 0
    timetables_created = 0
    
    # Pre-fetch existing caches to avoid duplicate queries
    existing_routes = await route_repo.get_multi(db, limit=5000)
    routes_cache = {r.route_number: r for r in existing_routes}
    
    existing_stops = await stop_repo.get_multi(db, limit=5000)
    stops_cache = {s.name: s for s in existing_stops}
    
    for row in extracted_rows:
        route_num = row.route_code.strip()
        dest_name = row.destination.strip()
        
        # Parse source stop name from sector
        # E.g. "SALEM TBS TO JUNCTION SECTOR" -> "Salem TBS"
        sector_upper = row.sector.upper()
        if " TO " in sector_upper:
            source_name = row.sector.split(" TO ")[0].strip()
        else:
            source_name = "Salem Town Bus Stand"
            
        # Clean up names
        source_name = source_name.replace("SECTOR", "").strip()
        
        # 1. Ensure source stop exists
        if source_name not in stops_cache:
            new_stop = await stop_repo.create(
                db,
                obj_in={
                    "name": source_name,
                    "latitude": 11.6643,
                    "longitude": 78.1460,
                    "address": "Salem, Tamil Nadu"
                }
            )
            stops_cache[source_name] = new_stop
            stops_created += 1
        source_stop = stops_cache[source_name]
        
        # 2. Ensure destination stop exists
        if dest_name not in stops_cache:
            new_stop = await stop_repo.create(
                db,
                obj_in={
                    "name": dest_name,
                    "latitude": 11.6500,
                    "longitude": 78.1500,
                    "address": "Salem, Tamil Nadu"
                }
            )
            stops_cache[dest_name] = new_stop
            stops_created += 1
        dest_stop = stops_cache[dest_name]
        
        # 3. Ensure route exists
        if route_num not in routes_cache:
            new_route = await route_repo.create(
                db,
                obj_in={
                    "route_number": route_num,
                    "source": source_name,
                    "destination": dest_name,
                    "description": f"Salem to {dest_name} (Operator: {row.operator})",
                    "fare": 25.0,
                    "frequency": "20 mins",
                    "trip_duration": "45 mins"
                }
            )
            routes_cache[route_num] = new_route
            routes_created += 1
            
            # Map route stops
            await route_stop_repo.create(
                db,
                obj_in={
                    "route_id": new_route.id,
                    "stop_id": source_stop.id,
                    "sequence_order": 1
                }
            )
            await route_stop_repo.create(
                db,
                obj_in={
                    "route_id": new_route.id,
                    "stop_id": dest_stop.id,
                    "sequence_order": 2
                }
            )
        route_obj = routes_cache[route_num]
        
        # 4. Ensure timetable slot exists
        # Parse arrival/departure time
        arr_time = None
        dep_time = None
        if row.arrival_time_normalized:
            try:
                arr_time = datetime.strptime(row.arrival_time_normalized, "%H:%M").time()
            except:
                pass
        if row.departure_time_normalized:
            try:
                dep_time = datetime.strptime(row.departure_time_normalized, "%H:%M").time()
            except:
                pass
                
        if dep_time:
            # Check if this timetable entry already exists
            t_query = select(timetable_repo.model).filter(
                and_(
                    timetable_repo.model.route_id == route_obj.id,
                    timetable_repo.model.stop_id == source_stop.id,
                    timetable_repo.model.departure_time == dep_time
                )
            )
            t_res = await db.execute(t_query)
            existing_t = t_res.scalars().first()
            
            if not existing_t:
                await timetable_repo.create(
                    db,
                    obj_in={
                        "route_id": route_obj.id,
                        "stop_id": source_stop.id,
                        "arrival_time": arr_time or dep_time,
                        "departure_time": dep_time,
                        "day_of_week": "ALL"
                    }
                )
                timetables_created += 1
                
    await db.commit()
    
    return StandardResponse(
        success=True,
        message=f"Successfully published staging data.",
        data={
            "routes_created": routes_created,
            "stops_created": stops_created,
            "timetables_created": timetables_created
        }
    )
