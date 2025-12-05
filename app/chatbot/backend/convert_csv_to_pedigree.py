"""
Script that takes in a complete csv file that is structured like:

id,relation,name,birthday,sex,is_dead,dad_id,mom_id,partner_id,disease1,
    disease2,disease3,disease4
    - where disease[1-4] can be any disease name

Takes this script and creates R code to work with kinship2
Added sleep for dramatic effect

This script corrects input order to siblings based on year of birth
Additionally, the script is able to handle csv files that contain less than 4
disease headings

There is no other error checking on either the file or data in the file
"""
import csv
import time
import subprocess
import os
import re
from collections import defaultdict

# Constants
DISEASE1_HEADER = 9
DISEASE2_HEADER = 10
DISEASE3_HEADER = 11
DISEASE4_HEADER = 12


def fix_sibling_orders(csv_filename):
    """
    Creates new csv file reordered based on sibling ages
    Siblings are listed from oldest to youngest
    Does not change id of individuals, only re-orders them
    Removes 'partner_id' column in the output csv to avoid confusion in R.
    """

    new_csv_name = "../results/ordered_patients.csv" 

    sibling_rows = defaultdict(list)
    rows_no_parents = []

    with open(csv_filename, mode='r') as file:
        reader = csv.DictReader(file)
        header = reader.fieldnames

        for row in reader:
            did = row['dad_id']
            mid = row['mom_id']

            if did != '0' and mid != '0':
                pkey = (did, mid)
                sibling_rows[pkey].append(row)
            else:
                rows_no_parents.append(row)

    for key in sibling_rows:
        sibling_rows[key].sort(key=lambda r: int(r['birthday'][:4]))

    ordered_rows = []
    ordered_rows.extend(rows_no_parents)

    for key in sibling_rows:
        ordered_rows.extend(sibling_rows[key])

    # Remove 'partner_id' from header and rows before writing
    if 'partner_id' in header:
        header.remove('partner_id')

    # Also remove partner_id from each row dictionary
    for row in ordered_rows:
        if 'partner_id' in row:
            del row['partner_id']

    with open(new_csv_name, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(ordered_rows)

    return new_csv_name, header


def create_data_frames(filename, data_frame):
    """
    Takes in csv file and extracts columns dynamically for diseases.
    Assumes standard columns: id,first_name,last_name,birthday,sex,is_dead,dad_id,mom_id,partner_id
    Disease columns start at index 9 and can be between 1 to 4.
    """

    print("Creating R dataframes ...")

    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames

        # Identify disease columns dynamically (starting from index 9)
        disease_columns = headers[9:]  # could be 1 to 4 disease columns

        for row in reader:
            data_frame["id"].append(row["id"])
            full_name = row["first_name"].strip() + " " + row["last_name"].strip()
            data_frame["name"].append(full_name + " (b. " + row["birthday"][:4] + ")")
            data_frame["dad_id"].append(row["dad_id"])
            data_frame["mom_id"].append(row["mom_id"])
            data_frame["sex"].append(row["sex"])
            data_frame["dead"].append(row["is_dead"])

            # Clear previous disease data just in case
            for i in range(1, 5):
                data_frame[f"disease{i}"].append("0")

            # Fill disease data only for present columns
            for i, disease_col in enumerate(disease_columns, 1):
                data_frame[f"disease{i}"][-1] = row[disease_col]

    time.sleep(3)
    print("Extracted!")


def translate_data_frame(data_frame, headers):
    """
    Creates R strings dynamically for available disease columns.
    """

    print("Translating dataframes ...")

    id_str = "c(" + ",".join(data_frame["id"]) + ")"
    name_dob_str = "c(\"" + "\",\"".join(data_frame["name"]) + "\")"
    dadid_str = "c(" + ",".join(data_frame["dad_id"]) + ")"
    mom_id_str = "c(" + ",".join(data_frame["mom_id"]) + ")"
    sex_str = "c(" + ",".join(data_frame["sex"]) + ")"
    dead_str = "c(" + ",".join(data_frame["dead"]) + ")"

    # Disease strings container
    disease_strs = []

    # Identify disease columns dynamically
    disease_columns = headers[9:]

    for i, disease_col in enumerate(disease_columns, 1):
        d_str = f"'{disease_col}'=c(" + ",".join(data_frame[f"disease{i}"]) + ")"
        # Skip if all empty or commas only
        if not re.search(r'=c\(,+\)', d_str):
            disease_strs.append(d_str)

    # Pad disease_strs with empty strings if less than 4 for unpacking later
    while len(disease_strs) < 4:
        disease_strs.append("")

    time.sleep(2)
    print("Done!")

    return id_str, name_dob_str, dadid_str, mom_id_str, sex_str, dead_str, \
           disease_strs[0], disease_strs[1], disease_strs[2], disease_strs[3]


def create_r_code(ped_id, name_dob, dad_id, mom_id, sex, dead, dis1, dis2, dis3, dis4):
    """
    returns r code
    aff <- data.frame(disease1_name=disease, ...)

    # ped <- pedigree(id, dad_id, mom_id, sex, affected, status)
    ped <- pedigree(id, dad_id, mom_id, sex, affected=as.matrix(aff), status=dead)

    plotnames <- paste(id, name_dob, sep="\n")
    
    # save as png
    png(filename="../results/fam_pedigree.png", width=1000, height=800, res=100)

    # plot with names & dob
    plot(ped, id=plotnames)

    pedigree.legend(ped, location="bottomleft", radius=0.3)

    # saves the ped plot with legend to curr working directory
    dev.off()
    """

    print("Creating R code ...")

    library_str = """if (!requireNamespace("kinship2", quietly = TRUE)) {
        install.packages("kinship2")
    }
    
    library(kinship2)\n\n"""

    all_diseases = ", ".join(dis for dis in [dis1, dis2, dis3, dis4] if dis)
    aff_str = "aff <- data.frame(" + all_diseases + ")\n\n"

    ped_str = "ped <- pedigree(" + ped_id + ", " + dad_id + ", " + mom_id + ", " + sex \
              + ", " + "affected=as.matrix(aff), " + "status=" + dead + ")\n\n"

    capture_plot_start = 'png(filename="../results/fam_pedigree.png", width=1600, height=1200, res=120)\n\n'

    margin_str = "par(mar=c(5,10,5,10))\n\n"

    plotnames_str = "plotnames <- paste(" + ped_id + ", " + name_dob + r', sep="\n")' + "\n\n"

    plot_str = "plot(ped, id=plotnames, cex=1)\n\n"

    ped_legend_str = 'pedigree.legend(ped, location="bottomright", radius=0.2)\n\n'

    capture_plot_end = "dev.off()\n"

    r_code_str = (library_str + aff_str + ped_str + capture_plot_start +
                  margin_str + plotnames_str + plot_str + ped_legend_str + capture_plot_end)

    time.sleep(4)
    print("Complete!")

    return r_code_str


def download_ped_plot(ped_filename):
    """
    Takes the generated R code and uses subprocess to capture the downloaded
    pedigree plot
    """
    print("Downloading...")

    try:
        subprocess.run(["Rscript", ped_filename], capture_output=True, check=True, text=True)

        print("R script has succeeded")
        if os.path.exists("../results/fam_pedigree.png"):
            print("Plot saved as '../results/fam_pedigree.png'")
            print("All Done!")
        else:
            print("Plot file not found")

    except subprocess.CalledProcessError as e:
        print("R script failed. Could not create your pedigree\n")
        print(f"STDERR: \n{e.stderr}")

    time.sleep(1)


def main():
    csv_filename = "../results/patients.csv"

    data_frame = {
        "id": [],
        "name": [],
        "mom_id": [],
        "dad_id": [],
        "sex": [],
        "dead": [],
        "disease1": [],
        "disease2": [],
        "disease3": [],
        "disease4": []
    }

    ped_code_filename = "../results/pedigree_code.R"

    # Step 1: Reorder siblings and prepare CSV
    new_csv_file, headers = fix_sibling_orders(csv_filename)

    # Step 2: Create Python-side data structure
    create_data_frames(new_csv_file, data_frame)

    # Step 3: Translate into R-compatible strings
    ped_id, name_dob, dad_id, mom_id, sex, dead, dis1, dis2, dis3, dis4 = \
        translate_data_frame(data_frame, headers)

    # Step 4: Create R code
    pedigree_code = create_r_code(
        ped_id, name_dob, dad_id, mom_id, sex, dead,
        dis1, dis2, dis3, dis4
    )

    # Step 5: Save R code to file
    with open(ped_code_filename, mode="w") as ped_file:
        ped_file.write(pedigree_code)
    print(f"R code saved to: {ped_code_filename}")

    # Step 6: Automatically generate the pedigree plot
    download_ped_plot(ped_code_filename)

    # Step 7: Also print R code to console
    print("\nYour pedigree R code is:\n")
    print(pedigree_code)

    # Step 8: Remove ordered_patients.csv after everything is done
    if os.path.exists(new_csv_file):
        os.remove(new_csv_file)
        print(f"\nTemporary file deleted: {new_csv_file}")
    else:
        print(f"\nTemporary file not found for deletion: {new_csv_file}")

    print("\nAll outputs have been generated and cleanup completed.\n")


if __name__ == '__main__':
    main()