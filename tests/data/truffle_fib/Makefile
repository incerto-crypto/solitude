
DIR := ${CURDIR}

default:
	rm -f truffle_lib.tar.xz
	echo 'module.exports = { compilers: { solc: { version: "0.5.8"} } };' > ./truffle-config.js
	truffle compile
	python3 replace.py build/contracts/CallFibonacci.json "$(DIR)" "/tmp/truffle_fib"
	python3 replace.py build/contracts/Fibonacci.json "$(DIR)" "/tmp/truffle_fib"
	python3 replace.py build/contracts/Migrations.json "$(DIR)" "/tmp/truffle_fib"
	tar -cJf truffle_fib.tar.xz build
