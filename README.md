# EasyCP

EasyCP is a plugin for ST3, which can parse the inputted url and scrap out the sample input and sample output testcases. Further it can run 
your code on those sample inputs and compares the output so obtained with the given sample output!  

EascyCP allows you to parse all tasks from the problemset at once, so in 2 clicks you can get all tests from the contest!

### Requirements

-  Languages supported: **Java**, **C++**, **Python 3**
-  Websites supported: **[Codeforces](https://codeforces.com "Visit codeforces.com")**

### Usage

First of all, go to `Preferences > Package Settings > EasyCP settings` and edit compile and run commands. 

-  Go to `Easy CP -> Parse Test-cases` in the menu bar, to scrap sample testcases.
-  Enter the url in the "Input URL" box at the bottom of the screen.
-  Go to `Easy CP -> Compile` in the menu bar to compile your code.
-  Go to `Easy CP -> Run` in the menu bar to execute your code on the sample testcases.

>  **NOTE:**
>
>  If you parse only one task, test cases will be associated with the current file name, for example if file name is `Task_B`, then test cases folder will be called `EasyCP_Task_B`.
>
>  If you parse the entire problemset, then test cases will be created with file names equal to the letters of the problems, so you have to name your files accordingly, for example, `A.py`,` E.cpp`, `D.java` (not `Tesk_E.py` or `f.cpp`).
>
> However, you can always change names simply by renaming the EasyCP folder, for example, changing `EasyCP_A` => `EasyCP_mytask` and `A.cpp` => `mytask.cp` will work as well.

---

##### *License: MIT*