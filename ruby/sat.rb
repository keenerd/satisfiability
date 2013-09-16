#!/usr/bin/ruby

cnf_line = lambda do |line|
  puts line.push(0).map(&:to_s).join(' ')
end

def neg cells
  return cells.map(&:-@)
end

# callback to prevent OOM
def window cells, a, b, callback
  cells.combination(cells.length + 1 - a).each do |cs|
    callback.call cs
  end
  cells.combination(b + 1).each do |cs|
    callback.call neg(cs)
  end
end

# window([1,2,3,4,5,6], 1, 2, cnf_line)

