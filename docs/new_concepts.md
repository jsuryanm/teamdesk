## Pooling in DB

- DB Pool size is the number of pre-opened, reusable connections that an application keeps ready to talk to a database.

- Imagine your application is a coffee shop, the database is the espresso machine, and the connections are baristas:
    - Without a connection pool (Pool Size = 0). Every time a customer orders a coffee, the shop has to hire, train, and put an apron on a brand-new barista, make one drink, and then send the barista home. Customers wait forever in line.
    
    - With a connection pool (Pool Size = 5). The shop keeps 5 trained baristas standing behind the counter ready to work.
	    - When 3 customers walk in, 3 baristas make their drinks right away and then return to waiting at the counter for the next order.
	    - If 8 customers walk in at once, 5 get served immediately, while the other 3 wait a brief moment until one of the 5 baristas finishes a drink.


## JWT (Json Web Token)
A compact, secure way for two parties (usually a user's browser and a website's server) to verify who you are without the server having to look you up in a database every single time you click a link. 

ex, VIP area in a concert, We will show the ticket and ID at front counter. The staff will give a VIP wristband (JWT). You can just use the wristband to enter the VIP area. 