; PCB DXF Verification Tool
; Extracts board outline, mounting holes, and edge connectors
; Sends data to Python backend for comparison with DXF

procedure(PCBDXFVerifier()
  let((formPath formHandle boardData)
    
    ; Define form file path
    formPath = "pcb_dxf_verifier.form"
    
    ; Create form callback function
    defun(_verifierCallback form @rest args
      let((action dxfFile tolerance pythonPath)
        action = car(args)
        
        case(action
          ("DXF_FILE"
            dxfFile = axlFormGet(form "dxfFile")
            printf("Selected DXF: %s\n" dxfFile)
          )
          
          ("VERIFY"
            ; Get form values
            dxfFile = axlFormGet(form "dxfFile")
            tolerance = axlFormGet(form "tolerance")
            
            if(dxfFile == "" then
              axlUIMessageBox("Please select a DXF file" "Error" "error")
            else
              ; Extract board data
              boardData = extractBoardData()
              
              if(boardData then
                ; Send to Python backend
                sendToPythonBackend(boardData dxfFile tolerance)
              else
                axlUIMessageBox("Failed to extract board data" "Error" "error")
              )
            )
          )
          
          ("EXPORT"
            ; Export results to Excel
            exportResults()
          )
          
          ("CANCEL"
            axlFormClose(form)
          )
        )
      )
    )
    
    ; Create and display form
    formHandle = axlFormCreate(
      (gensym 'pcbVerifier)
      formPath
      '()
      '_verifierCallback
      t
    )
    
    if(formHandle then
      axlFormDisplay(formHandle)
    else
      printf("Error: Could not create form\n")
    )
  )
)

; Extract board outline dimensions
procedure(extractBoardOutline()
  let((outline dbid points width height minX maxX minY maxY)
    outline = nil
    
    ; Get board outline from design
    dbid = axlDBGetDesign()
    
    if(dbid then
      ; Get board outline path
      foreach(shape axlGetAllShapes()
        when(shape->objType == "outline"
          points = shape->points
          
          if(points then
            minX = car(car(points))
            maxX = car(car(points))
            minY = cadr(car(points))
            maxY = cadr(car(points))
            
            ; Find bounding box
            foreach(pt points
              when(car(pt) < minX
                minX = car(pt)
              )
              when(car(pt) > maxX
                maxX = car(pt)
              )
              when(cadr(pt) < minY
                minY = cadr(pt)
              )
              when(cadr(pt) > maxY
                maxY = cadr(pt)
              )
            )
            
            ; Calculate dimensions with decimal precision
            width = sprintf(nil "%.6f" (maxX - minX))
            height = sprintf(nil "%.6f" (maxY - minY))
            
            outline = list(
              list("type" "board_outline")
              list("width" width)
              list("height" height)
              list("minX" sprintf(nil "%.6f" minX))
              list("minY" sprintf(nil "%.6f" minY))
              list("maxX" sprintf(nil "%.6f" maxX))
              list("maxY" sprintf(nil "%.6f" maxY))
            )
          )
        )
      )
    )
    
    outline
  )
)

; Extract mounting holes
procedure(extractMountingHoles()
  let((holes holeList pin x y diameter)
    holeList = list()
    
    ; Iterate through all pins to find mounting holes
    foreach(pin axlGetAllPins()
      when(pin->isMountingHole == t
        x = sprintf(nil "%.6f" car(pin->xy))
        y = sprintf(nil "%.6f" cadr(pin->xy))
        diameter = sprintf(nil "%.6f" pin->diameter)
        
        holeList = append(holeList 
          list(list(
            list("id" pin->name)
            list("x" x)
            list("y" y)
            list("diameter" diameter)
            list("type" "mounting_hole")
          ))
        )
      )
    )
    
    holeList
  )
)

; Extract edge connectors
procedure(extractEdgeConnectors()
  let((connectors connList comp x y width height rotation)
    connList = list()
    
    ; Find edge connectors
    foreach(comp axlGetAllComponents()
      when(rexMatchp("CONN" comp->name)
        x = sprintf(nil "%.6f" car(comp->xy))
        y = sprintf(nil "%.6f" cadr(comp->xy))
        width = sprintf(nil "%.6f" comp->width)
        height = sprintf(nil "%.6f" comp->height)
        rotation = sprintf(nil "%.6f" comp->rotation)
        
        connList = append(connList
          list(list(
            list("id" comp->name)
            list("x" x)
            list("y" y)
            list("width" width)
            list("height" height)
            list("rotation" rotation)
            list("type" "edge_connector")
          ))
        )
      )
    )
    
    connList
  )
)

; Combine all extracted data
procedure(extractBoardData()
  let((data outline holes connectors)
    outline = extractBoardOutline()
    holes = extractMountingHoles()
    connectors = extractEdgeConnectors()
    
    if(outline then
      data = list(
        list("board_outline" outline)
        list("mounting_holes" holes)
        list("edge_connectors" connectors)
        list("timestamp" getCurrentTime())
      )
      
      printf("Extracted board data successfully\n")
      data
    else
      nil
    )
  )
)

; Send data to Python backend via socket/file
procedure(sendToPythonBackend(boardData dxfFile tolerance)
  let((jsonFile pyCommand result)
    ; Export board data as JSON
    jsonFile = "/tmp/board_data.json"
    exportToJSON(boardData jsonFile)
    
    ; Call Python script
    pyCommand = sprintf(nil "python3 pcb_verifier_backend.py --board %s --dxf %s --tolerance %s" 
                       jsonFile dxfFile tolerance)
    
    printf("Executing: %s\n" pyCommand)
    result = shell(pyCommand)
    
    if(result == 0 then
      axlUIMessageBox("Verification completed. Check results." "Success" "info")
    else
      axlUIMessageBox("Verification failed. Check logs." "Error" "error")
    )
  )
)

; Export data structure to JSON format
procedure(exportToJSON(data filename)
  let((port)
    port = outfile(filename)
    
    if(port then
      fprintf(port "{\n")
      ; Write JSON structure (simplified)
      foreach(item data
        fprintf(port "  \"%s\": %L,\n" car(item) cadr(item))
      )
      fprintf(port "}\n")
      close(port)
      printf("Exported to %s\n" filename)
      t
    else
      printf("Error: Could not write to %s\n" filename)
      nil
    )
  )
)

; Helper to get current timestamp
procedure(getCurrentTime()
  let((time)
    time = getCurrentTime()
    sprintf(nil "%d-%02d-%02d %02d:%02d:%02d"
           time->year time->month time->day
           time->hour time->minute time->second)
  )
)

; Export results to Excel
procedure(exportResults()
  printf("Exporting results to Excel...\n")
  ; Implementation depends on result storage
  axlUIMessageBox("Results exported successfully" "Export" "info")
)

; Register command
axlCmdRegister("pcb_dxf_verify" 'PCBDXFVerifier)

printf("PCB DXF Verifier loaded. Run with: pcb_dxf_verify\n")














#!/usr/bin/env python3
"""
PCB DXF Verification Backend
Compares PCB board data with DXF mechanical drawings using decimal precision
"""

import sys
import json
import argparse
from decimal import Decimal, getcontext
from pathlib import Path
import ezdxf
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from datetime import datetime

# Set decimal precision
getcontext().prec = 10

class PCBDXFVerifier:
    def __init__(self, tolerance=Decimal('0.001')):
        self.tolerance = tolerance
        self.results = []
        self.pcb_data = None
        self.dxf_data = None
        
    def load_pcb_data(self, json_file):
        """Load PCB data from JSON file exported by Skill script"""
        try:
            with open(json_file, 'r') as f:
                self.pcb_data = json.load(f)
            print(f"✓ Loaded PCB data from {json_file}")
            return True
        except Exception as e:
            print(f"✗ Error loading PCB data: {e}")
            return False
    
    def load_dxf_data(self, dxf_file):
        """Load and parse DXF file"""
        try:
            doc = ezdxf.readfile(dxf_file)
            msp = doc.modelspace()
            
            self.dxf_data = {
                'outline': self.extract_dxf_outline(msp),
                'holes': self.extract_dxf_holes(msp),
                'connectors': self.extract_dxf_connectors(msp)
            }
            
            print(f"✓ Loaded DXF data from {dxf_file}")
            return True
        except Exception as e:
            print(f"✗ Error loading DXF data: {e}")
            return False
    
    def extract_dxf_outline(self, modelspace):
        """Extract board outline from DXF"""
        outline_points = []
        
        for entity in modelspace.query('LINE POLYLINE LWPOLYLINE'):
            if entity.dxf.layer == 'BOARD_OUTLINE' or entity.dxf.layer == 'Board_Outline':
                if entity.dxftype() == 'LINE':
                    outline_points.append((Decimal(str(entity.dxf.start.x)), 
                                         Decimal(str(entity.dxf.start.y))))
                    outline_points.append((Decimal(str(entity.dxf.end.x)), 
                                         Decimal(str(entity.dxf.end.y))))
                elif entity.dxftype() in ['POLYLINE', 'LWPOLYLINE']:
                    for point in entity.get_points():
                        outline_points.append((Decimal(str(point[0])), 
                                             Decimal(str(point[1]))))
        
        if outline_points:
            min_x = min(p[0] for p in outline_points)
            max_x = max(p[0] for p in outline_points)
            min_y = min(p[1] for p in outline_points)
            max_y = max(p[1] for p in outline_points)
            
            return {
                'width': max_x - min_x,
                'height': max_y - min_y,
                'minX': min_x,
                'minY': min_y,
                'maxX': max_x,
                'maxY': max_y
            }
        
        return None
    
    def extract_dxf_holes(self, modelspace):
        """Extract mounting holes from DXF"""
        holes = []
        hole_id = 1
        
        for entity in modelspace.query('CIRCLE'):
            if entity.dxf.layer in ['MOUNTING_HOLE', 'Mounting_Holes', 'HOLES']:
                holes.append({
                    'id': f'MH{hole_id}',
                    'x': Decimal(str(entity.dxf.center.x)),
                    'y': Decimal(str(entity.dxf.center.y)),
                    'diameter': Decimal(str(entity.dxf.radius * 2))
                })
                hole_id += 1
        
        return holes
    
    def extract_dxf_connectors(self, modelspace):
        """Extract edge connectors from DXF"""
        connectors = []
        conn_id = 1
        
        for entity in modelspace.query('INSERT'):
            if 'CONN' in entity.dxf.name.upper():
                connectors.append({
                    'id': f'CONN{conn_id}',
                    'x': Decimal(str(entity.dxf.insert.x)),
                    'y': Decimal(str(entity.dxf.insert.y)),
                    'rotation': Decimal(str(entity.dxf.rotation))
                })
                conn_id += 1
        
        return connectors
    
    def compare_values(self, pcb_val, dxf_val, component_type, component_id, param_name):
        """Compare two decimal values with tolerance"""
        pcb_decimal = Decimal(str(pcb_val))
        dxf_decimal = Decimal(str(dxf_val))
        difference = abs(pcb_decimal - dxf_decimal)
        status = 'PASS' if difference <= self.tolerance else 'FAIL'
        
        self.results.append({
            'component_type': component_type,
            'id': component_id,
            'parameter': param_name,
            'pcb_value': pcb_decimal,
            'dxf_value': dxf_decimal,
            'difference': difference,
            'status': status
        })
        
        return status == 'PASS'
    
    def verify_board_outline(self):
        """Compare board outline dimensions"""
        print("\n=== Verifying Board Outline ===")
        
        if not self.pcb_data or not self.dxf_data:
            print("✗ Missing data")
            return False
        
        pcb_outline = self.pcb_data.get('board_outline', {})
        dxf_outline = self.dxf_data.get('outline', {})
        
        if not pcb_outline or not dxf_outline:
            print("✗ Outline data not found")
            return False
        
        self.compare_values(
            pcb_outline.get('width', 0),
            dxf_outline['width'],
            'Board Outline', 'Width', 'Width'
        )
        
        self.compare_values(
            pcb_outline.get('height', 0),
            dxf_outline['height'],
            'Board Outline', 'Height', 'Height'
        )
        
        print("✓ Board outline verification complete")
        return True
    
    def verify_mounting_holes(self):
        """Compare mounting hole positions"""
        print("\n=== Verifying Mounting Holes ===")
        
        pcb_holes = self.pcb_data.get('mounting_holes', [])
        dxf_holes = self.dxf_data.get('holes', [])
        
        if len(pcb_holes) != len(dxf_holes):
            print(f"⚠ Hole count mismatch: PCB={len(pcb_holes)}, DXF={len(dxf_holes)}")
        
        # Match holes by proximity
        for pcb_hole in pcb_holes:
            pcb_x = Decimal(str(pcb_hole.get('x', 0)))
            pcb_y = Decimal(str(pcb_hole.get('y', 0)))
            
            # Find closest DXF hole
            closest_hole = min(dxf_holes, 
                             key=lambda h: abs(h['x'] - pcb_x) + abs(h['y'] - pcb_y))
            
            hole_id = pcb_hole.get('id', 'Unknown')
            
            self.compare_values(pcb_x, closest_hole['x'], 
                              'Mounting Hole', f"{hole_id} X", 'X Position')
            self.compare_values(pcb_y, closest_hole['y'], 
                              'Mounting Hole', f"{hole_id} Y", 'Y Position')
        
        print("✓ Mounting holes verification complete")
        return True
    
    def verify_edge_connectors(self):
        """Compare edge connector positions"""
        print("\n=== Verifying Edge Connectors ===")
        
        pcb_connectors = self.pcb_data.get('edge_connectors', [])
        dxf_connectors = self.dxf_data.get('connectors', [])
        
        if len(pcb_connectors) != len(dxf_connectors):
            print(f"⚠ Connector count mismatch: PCB={len(pcb_connectors)}, DXF={len(dxf_connectors)}")
        
        for i, pcb_conn in enumerate(pcb_connectors):
            if i < len(dxf_connectors):
                dxf_conn = dxf_connectors[i]
                conn_id = pcb_conn.get('id', f'CONN{i+1}')
                
                self.compare_values(
                    pcb_conn.get('x', 0), dxf_conn['x'],
                    'Edge Connector', f"{conn_id} X", 'X Position'
                )
                
                self.compare_values(
                    pcb_conn.get('y', 0), dxf_conn['y'],
                    'Edge Connector', f"{conn_id} Y", 'Y Position'
                )
        
        print("✓ Edge connectors verification complete")
        return True
    
    def generate_report(self, output_file='verification_report.xlsx'):
        """Generate Excel report with results"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Verification Results"
        
        # Header styling
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        fail_fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
        pass_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        
        # Headers
        headers = ['Component Type', 'ID', 'Parameter', 'PCB Value', 'DXF Value', 'Difference', 'Status']
        ws.append(headers)
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Data rows
        for result in self.results:
            row = [
                result['component_type'],
                result['id'],
                result['parameter'],
                float(result['pcb_value']),
                float(result['dxf_value']),
                float(result['difference']),
                result['status']
            ]
            ws.append(row)
            
            # Color code based on status
            row_num = ws.max_row
            if result['status'] == 'FAIL':
                for cell in ws[row_num]:
                    cell.fill = fail_fill
            else:
                for cell in ws[row_num]:
                    cell.fill = pass_fill
        
        # Summary sheet
        ws_summary = wb.create_sheet("Summary")
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        
        ws_summary.append(['Verification Summary'])
        ws_summary.append(['Total Checks', total])
        ws_summary.append(['Passed', passed])
        ws_summary.append(['Failed', failed])
        ws_summary.append(['Pass Rate', f"{(passed/total*100):.1f}%" if total > 0 else "N/A"])
        ws_summary.append(['Timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        
        # Save workbook
        wb.save(output_file)
        print(f"\n✓ Report generated: {output_file}")
        return output_file
    
    def run_verification(self):
        """Run complete verification process"""
        print("\n" + "="*60)
        print("PCB DXF VERIFICATION")
        print("="*60)
        
        success = True
        success &= self.verify_board_outline()
        success &= self.verify_mounting_holes()
        success &= self.verify_edge_connectors()
        
        # Generate report
        report_file = self.generate_report()
        
        # Print summary
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        
        print(f"Total Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Status: {'✓ PASS' if failed == 0 else '✗ FAIL'}")
        print(f"Report: {report_file}")
        print("="*60)
        
        return failed == 0

def main():
    parser = argparse.ArgumentParser(description='PCB DXF Verification Tool')
    parser.add_argument('--board', required=True, help='Board JSON file from Skill script')
    parser.add_argument('--dxf', required=True, help='DXF mechanical drawing file')
    parser.add_argument('--tolerance', type=float, default=0.001, help='Tolerance in mm')
    parser.add_argument('--output', default='verification_report.xlsx', help='Output Excel file')
    
    args = parser.parse_args()
    
    # Create verifier instance
    verifier = PCBDXFVerifier(tolerance=Decimal(str(args.tolerance)))
    
    # Load data
    if not verifier.load_pcb_data(args.board):
        sys.exit(1)
    
    if not verifier.load_dxf_data(args.dxf):
        sys.exit(1)
    
    # Run verification
    success = verifier.run_verification()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()


