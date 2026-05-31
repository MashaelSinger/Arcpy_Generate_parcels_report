import arcpy
import os

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "ParcelToolbox"
        self.alias = "parceltools"
        self.tools = [GenerateParcelReport]

class GenerateParcelReport:
    def __init__(self):
        self.label = "Generate Parcel Report"
        self.description = "Analyzes building data per parcel using geometry checks."

    def getParameterInfo(self):

        params = [
            arcpy.Parameter(name="parcel_layer", displayName="Parcel Layer", datatype="GPFeatureLayer", parameterType="Required", direction="Input"),
            arcpy.Parameter(name="building_layer", displayName="Building Layer", datatype="GPFeatureLayer", parameterType="Required", direction="Input"),
            arcpy.Parameter(name="output_table", displayName="Output Table", datatype="DETable", parameterType="Required", direction="Output")
        ]
        return params

    def execute(self, parameters, messages):
        #add try catch to handle error and show it if any error occured 
        try: 
            parcel_lyr = parameters[0].valueAsText
            building_lyr = parameters[1].valueAsText
            out_table = parameters[2].valueAsText
            
            out_path = os.path.dirname(out_table)
            out_name = os.path.basename(out_table)

            if arcpy.Exists(out_table):
                arcpy.AddMessage(f"Table {out_name} already exists. Overwriting.")
                arcpy.management.Delete(out_table)
            
            arcpy.management.CreateTable(out_path, out_name)
            arcpy.management.AddField(out_table, "Parcel_Name", "TEXT")
            arcpy.management.AddField(out_table, "Inside_Buildings_Code", "TEXT", field_length=500)
            arcpy.management.AddField(out_table, "Total_Residential_Area", "DOUBLE")
            arcpy.management.AddField(out_table, "Total_Commercial_Area", "DOUBLE")
            arcpy.AddMessage("Output table and fields initialized.")

            parcel_results = {}
            building_found = False #to use it in the warning if no buildings are found in all the parcels

            with arcpy.da.SearchCursor(parcel_lyr, ["OID@", "Parcel_ID", "SHAPE@"]) as p_cursor:
                for p_row in p_cursor:
                    p_oid, p_id, p_geom = p_row
                    parcel_results[p_oid] = {"id": str(p_id), "codes": [], "resd": 0.0, "com": 0.0}
                    
                    with arcpy.da.SearchCursor(building_lyr, ["Building_Code", "primary_use", "SHAPE@"]) as b_cursor:
                        for b_row in b_cursor:
                            b_code, b_use, b_geom = b_row
                            #imp_note: use contains because when i used spatial join it always considered all parcels as one parcel and couldnot solve it#####
                            if p_geom.contains(b_geom):
                                parcel_results[p_oid]["codes"].append(str(b_code))
                                area = b_geom.area
                                if b_use == 'resd':
                                    parcel_results[p_oid]["resd"] += area
                                elif b_use == 'com':
                                    parcel_results[p_oid]["com"] += area
                                building_found = True

            
            if not building_found:
                arcpy.AddWarning("No buildings were found inside any of the provided parcels.")

            with arcpy.da.InsertCursor(out_table, ["Parcel_Name", "Inside_Buildings_Code", "Total_Residential_Area", "Total_Commercial_Area"]) as i_cursor:
                for data in parcel_results.values():
                    unique_codes = ", ".join(set(data["codes"]))
                    i_cursor.insertRow((data["id"], unique_codes, data["resd"], data["com"]))

            arcpy.AddMessage("Report generation complete.")

        except Exception as e:
            
            arcpy.AddError(f"An error occurred: {str(e)}")