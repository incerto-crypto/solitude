pragma solidity ^0.5.8;

import "./Fibonacci.sol";

contract CallFibonacci is Fibonacci
{
    uint public result;

    constructor() public {
        result = 0;
    }

    function fib(uint n) public {
        result = fib_r(n);
    }
}
