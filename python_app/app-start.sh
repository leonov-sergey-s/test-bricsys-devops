#!/bin/sh

echo "Input txt-files normalization:"

txt_origin_path=txt_files/origin
txt_normalized_path=txt_files/normalized
rm -f $txt_normalized_path/*.txt
for txt_file in $(find $txt_origin_path -name "*.txt" -type f); do
  new_txt_file=$txt_normalized_path/$(basename $txt_file)
  sed 's/ \t/\t/g;s/\t\t/\t/g;s/\r//g;/^$/d' $txt_file > $new_txt_file
  echo "$new_txt_file - ok"
done

echo "Await before MySQL container started"

./wait-for db:3306 -t 600 -- python app.py
