args <- commandArgs(trailingOnly = TRUE)
csv_file <- args[1]
output_file <- args[2]

library(kinship2)
df <- read.csv(csv_file, stringsAsFactors = FALSE)

ped <- with(df, pedigree(id = id,
                         dadid = dad_id,
                         momid = mom_id,
                         sex = ifelse(sex == 'male', 1, ifelse(sex == 'female', 2, NA)),
                         affected = ifelse(grepl("cancer|heart|diabetes", conditions, ignore.case = TRUE), 1, 0),
                         famid = rep(1, nrow(df))))

png(output_file, width = 1000, height = 600)

if (class(ped) == "pedigree") {
    plot(ped)
} else if (class(ped) == "pedigreeList" || is.list(ped)) {
    for (i in seq_along(ped)) {
        plot(ped[[i]])
    }
} else {
    stop("ped is not a valid pedigree object")
}

dev.off()

