ids = IO.readlines("temp.2")

counter = 0

ids.each do |id|
  print(id.strip().to_s + ", ")

  counter = counter + 1
  if counter == 10 then
    puts()
    counter = 0
  end
end
