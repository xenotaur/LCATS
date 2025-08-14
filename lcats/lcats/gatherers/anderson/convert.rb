def passWord(word) 
  if word == "is" or
    word == "a" or
    word == "the" then return true else return false
  end
end

def startWord(word)
  if word == "a" or word == "an" or word == "the" or word == "from" then return true else false end
end

titles = IO.readlines("anderson.txt")

titles.each do |title|
  if startWord(title.downcase.split()[0]) then 
    shortForm = title.downcase.split()[1..-1].map{|word| word}.join("_")
  else
    shortForm = title.downcase.split().map{|word| word}.join("_")
  end
  
  convertedTitle = title.downcase.split().map{|word| if !passWord(word) then word.capitalize() else word end}.join(" ")
  tempWords = convertedTitle.split()
  tempWords[0] = tempWords[0].capitalize()
  convertedTitle = tempWords.join(" ")
  
  puts ("('" + shortForm + "', '" + title.strip + "', '" + "Anderson - " + convertedTitle + "'),")
end


  
