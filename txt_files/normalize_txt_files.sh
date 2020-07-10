script_relative_path=$(dirname $0)
txt_origin_path=$script_relative_path/origin
txt_normalized_path=$script_relative_path/normalized

echo "\nInput txt-files normalization:"
rm -f $txt_normalized_path/*.txt
for txt_file in $(find $txt_origin_path -name *.txt -type f); do
  new_txt_file=$txt_normalized_path/$(basename $txt_file)
  sed 's/ \t/\t/g;s/\t\t/\t/g;s/\r//g;/^$/d' $txt_file > $new_txt_file
  echo "\t$new_txt_file - ok"
done
