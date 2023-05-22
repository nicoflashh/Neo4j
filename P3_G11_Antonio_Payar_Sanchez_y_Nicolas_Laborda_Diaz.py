__author__ = 'Antonio_Payar_Sánchez_y_Nicolás_Laborda_Díaz'
from neo4j import GraphDatabase
from datetime import datetime

class Modelo:

#Establecemos conexion
    def __init__(self,password):
        #Establecemos conexion
        self.conexion = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j",password))
        self.session =  self.conexion.session()
        self.id_pedidos=0
        self.id_vehiculos=0


    #Funcion para crear modelo
    def crearModelo(self,fichero):
        fichero=open(fichero)
        self.session.run(fichero.read()).values()
        #modelo = fichero.read()
        fichero.close()
        #return modelo

#Metodo auxiliar para modificar query, respecto al tipo que seleccione. 
    def __crearServicio(self,servicio):
        orderby="order by "

        if servicio=="tipo_01" or servicio=="tipo_02":
            orderby=orderby+"TIEMPO"
        elif servicio=="tipo_03":
            orderby=orderby+"PRECIO"
        
        return orderby

 #Metodo que calcula la ruta mas optima dependiendo del tipo  
    def calcularPrecioDistancia(self,origen,destino,tipo):
        
        resultado = self.session.run("MATCH (n:Ciudad{Nombre:$origen}), (n1:Ciudad{Nombre:$destino}),"
                            "p = allshortestpaths((n)-[*]->(n1))"
                            "RETURN reduce(total_distance = 0, n IN RELATIONSHIPS(p) | total_distance + n.distancia) AS DISTANCIA,"
                            "reduce(total_price = 0, n IN RELATIONSHIPS(p) | total_price + n.precio) AS PRECIO, "
                            "reduce(total_tiempo=0, n IN RELATIONSHIPS(p) | total_tiempo + n.tiempo) AS TIEMPO,"
                            "reduce (total_tipo = '', n IN RELATIONSHIPS(p) | total_tipo + '/'+ n.tipo) AS TIPO,"
                            "reduce(total_city = '', n IN nodes(p) | total_city + '/' + n.Nombre) AS CIUDADES "+ self.__crearServicio(tipo)
                            ,origen=origen,destino=destino)
        #TABLA
        #DISTANCIA-PRECIO-TIEMPO-TIPO-CIUDADES  
        listas=resultado.values()                      
        
        #Utilizamos la ruta primera que es la mas eficiente
        if(len(listas)>0):
            query_distancia =listas[0][0]
            query_precio =listas[0][1]
            query_tiempo =listas[0][2]
            query_tipo =listas[0][3]
            query_ciudades =listas[0][4]

            #Comprobamos que es posible el trayecto con el tiempo
            hora= datetime.now().strftime("%H")
            hora_pedido=0.0

            if tipo=="tipo_01":
                hora_pedido=(float(query_tiempo)/60)+float(hora)

                if(hora_pedido<18):
                    #Creamos el Envio
                    self.id_pedidos=self.id_pedidos+1
                    self.__creacionEnvio(self.id_pedidos,"Pedido_"+str(self.id_pedidos),tipo,query_precio,query_tipo,str(hora_pedido),origen,origen,destino)
                    #Creamos el Vehiculo
                    self.id_vehiculos=self.id_vehiculos+1
                    self.__creacionTransporte(self.id_vehiculos,"Vehiculo_"+str(self.id_vehiculos),origen,origen,tipo,query_tipo,query_ciudades)
                    #Creamos asociacion Envio->Transporte
                    self.__relacionEnvioTrasporte(str(self.id_pedidos),str(self.id_vehiculos))
                    #Creamos asociacion Transporte->Ciudad
                    self.__relacionTransporteCiudad("Vehiculo_"+str(self.id_vehiculos),origen)

                elif(hora_pedido<19):
                    raise Exception("No es posible realizarlo con el servicio "+tipo+" por el Tiempo de Empaquetamiento")
                else:
                    raise Exception("No es posible realizar ese trayecto con servicio "+tipo+" antes de las 19:00 ")
            elif tipo=="tipo_02":
                hora_pedido=((24-float(hora))+14)


                if((query_tiempo/60)>float(hora_pedido)):
                    raise Exception("No es posible realizar ese trayecto con servicio "+tipo+" antes de las 14:00 ")
 
            #Creamos el Envio tanto para el tipo_02 y el tipo_03
            self.id_pedidos=self.id_pedidos+1
            self.__creacionEnvio(self.id_pedidos,"Pedido_"+str(self.id_pedidos),tipo,query_precio,query_tipo,str(hora_pedido),origen,origen,destino)
            #Creamos el Vehiculo
            self.id_vehiculos=self.id_vehiculos+1
            self.__creacionTransporte(self.id_vehiculos,"Vehiculo_"+str(self.id_vehiculos),origen,origen,tipo,query_tipo,query_ciudades)
            #Creamos asociacion Envio->Transporte
            self.__relacionEnvioTrasporte(str(self.id_pedidos),str(self.id_vehiculos))
            #Creamos asociacion Transporte->Ciudad
            self.__relacionTransporteCiudad("Vehiculo_"+str(self.id_vehiculos),origen)
                
        else:
            raise Exception("No hay Trayectos para dichos puntos")

        

#Metodos privados para crear el envio, y su respectivo transporte
    def __creacionEnvio(self,id,id_pedido,servicio_pedido,coste_pedido,vehiculo_pedido,tiempo_pedido,ubi_act_pedido,ubi_ult_pedido,destino):

        #Creamos el Pedido
        self.session.run("CREATE (Pedido_"+str(id)+":Pedido{Nombre:$id_pedido,Servicio:$servicio_pedido,tiempo:$coste_pedido,vehiculo:$vehiculo_pedido,ubicacion_actual:$ubi_act_pedido,ubicacion_ultima:$ubi_ult_pedido,destino:$destino})"
                            ,id_pedido=id_pedido,servicio_pedido=servicio_pedido,coste_pedido=coste_pedido,vehiculo_pedido=vehiculo_pedido,tiempo_pedido=tiempo_pedido,ubi_act_pedido=ubi_act_pedido,ubi_ult_pedido=ubi_ult_pedido,destino=destino)


    def __creacionTransporte(self,id,id_transporte,nodo_anterior,nodo_actual,servicio_transporte,tipo_transporte,trayecto_transporte):

        #Creamos el Transporte
        self.session.run("CREATE (Vehiculo_"+str(id)+":Transporte{Nombre:$id_transporte,Tipo:$tipo_transporte,Servicio:$servicio_transporte,Nodo_actual:$nodo_actual,Nodo_anterior:$nodo_anterior,Trayecto:$trayecto_transporte})"
                            ,id_transporte=id_transporte,tipo_transporte=tipo_transporte,servicio_transporte=servicio_transporte,nodo_actual=nodo_actual,nodo_anterior=nodo_anterior,trayecto_transporte=trayecto_transporte)


#Metodo encargado de crear la relacion Pedido-Transporte
    def __relacionEnvioTrasporte(self,id_pedidos,id_transporte):

        self.session.run("MATCH (a:Pedido),(b:Transporte)"
                                "WHERE a.Nombre = 'Pedido_"+id_pedidos+"' AND b.Nombre = 'Vehiculo_"+id_transporte+"'"
                                "CREATE (a)-[r:DENTRO]->(b) "
                                "RETURN type(r)")
        
#Metodo privado utilizado para crear relaciones entre los transportes y las ciudades
    def __relacionTransporteCiudad(self,id_transporte,nombre_ciudad):

            #Eliminamos la asociacion anterior
        self.session.run("MATCH (n:Transporte{Nombre:'"+id_transporte+"'})-[r:ENVIO]->()"
                    "DELETE r")
        
        #Comprobamos que el nodo actual sea un almacen y modificamos la query
        if(len(nombre_ciudad)>=7 and nombre_ciudad[0:7]=="Almacen"):

            #Creamos la nueva asociacion
            self.session.run("MATCH (a:Transporte),(b:Almacen)"
            "WHERE a.Nombre = '"+id_transporte+"' AND b.Nombre = '"+nombre_ciudad+"'"
            "CREATE (a)-[r:ENVIO]->(b)"
            "RETURN type(r)")
        else:
            #Creamos la nueva asociacion
            self.session.run("MATCH (a:Transporte),(b:Ciudad)"
            "WHERE a.Nombre = '"+id_transporte+"' AND b.Nombre = '"+nombre_ciudad+"'"
            "CREATE (a)-[r:ENVIO]->(b)"
            "RETURN type(r)")

    
#Metodo privado utilizado para actualizar el tiempo del pedido
    def __consultaTiempo(self,nodo_actual,id_pedido):
      
        resultado=self.session.run("MATCH (n: Pedido{Nombre:$id_pedido}) return n.destino",id_pedido=id_pedido) 

        listas=resultado.values()
        nodo_destino=listas[0][0]

        #Comprobamos que el nodo actual sea un almacen y modificamos la query
        if(len(nodo_actual)>=7 and nodo_actual[0:7]=="Almacen"):
            resultado=self.session.run("MATCH  (n:Almacen{Nombre:$nodo_actual}),(n1:Ciudad{Nombre:$nodo_destino}),"
                            "p = allshortestpaths((n)-[*]->(n1))"
                            "RETURN reduce(total_tiempo = 0, n IN RELATIONSHIPS(p) | total_tiempo + n.tiempo) AS TIEMPO"
                            ,nodo_actual=nodo_actual,nodo_destino=nodo_destino)
        elif(nodo_destino==nodo_actual):
            return "0"
        else:
            resultado=self.session.run("MATCH  (n:Ciudad{Nombre:$nodo_actual}),(n1:Ciudad{Nombre:$nodo_destino}),"
                            "p = allshortestpaths((n)-[*]->(n1))"
                            "RETURN reduce(total_tiempo = 0, n IN RELATIONSHIPS(p) | total_tiempo + n.tiempo) AS TIEMPO"
                            ,nodo_actual=nodo_actual,nodo_destino=nodo_destino)

        listas=resultado.values()
        return listas[0][0]


#Metodo para actualizar la relacion Transporte-Ciudad
    def actualizacionEnvioTransporte(self,id_transporte,id_pedido):
        resultado=self.session.run("MATCH (n: Transporte{Nombre:$id_transporte})"
                        "return n.Trayecto",id_transporte=id_transporte)
        listas=resultado.values()

        #Spliteamos las ciudades
        ciudades=listas[0][0].split(sep='/')

        if(len(ciudades)>1):
            #Eliminamos la posicion 1 del las ciudades
            last_ciudad=ciudades.pop(1)

            #Almacenamos la siguiente posicion de las Ciudades
            next_ciudad=ciudades[1]            
        else:
            next_ciudad=ciudades[1]
            last_ciudad=ciudades[1] 

        resultado=self.session.run("MATCH (n: Transporte{Nombre:$id_transporte})"
                "return n.Tipo",id_transporte=id_transporte)
        listas=resultado.values()

        #Spliteamos los transportes
        transporte=listas[0][0].split(sep='/')

        if(len(transporte)>1):
            #Eliminamos la posicion 1 del los transportes
            transporte.pop(1)
            #Tenemos que crear un string nuevo con las nuevas ciudades y transportes
            string_transporte="/"
            for i in range(1,len(transporte)):        
                string_transporte=string_transporte+transporte[i]+"/"                       
        else:
            string_transporte="/"+transporte[1]+"/"  

        string_ciudades="/"
        for i in range(1,len(ciudades)):  
            string_ciudades=string_ciudades+ciudades[i]+"/"

        #Updateamos las variables con las direcciones y transportes actualizados en Transporte
        self.session.run("MATCH (n: Transporte{Nombre:$id_transporte})"
        "SET n.Tipo='"+string_transporte+"', n.Trayecto='"+string_ciudades+"' , n.Nodo_actual='"+next_ciudad+"', n.Nodo_anterior='"+last_ciudad+"'",id_transporte=id_transporte)
        
        #Finalmente creamos la relacion entre la nueva ciudad y el Transporte
        if(next_ciudad == ""):
            raise Exception("No es posible Actualizar la localizacion : El Transporte llego al ultimo Destino")
        else:
            #Updateamos las variables con las direcciones y transportes actualizados en Pedido
            self.session.run("MATCH (n: Pedido{Nombre:$id_pedido})"
            "SET n.ubicacion_actual='"+next_ciudad+"', n.ubicacion_ultima='"+last_ciudad+"' , n.vehiculo='"+string_transporte+"', n.tiempo='"+str(self.__consultaTiempo(next_ciudad,str(id_pedido)))+"'",id_pedido=id_pedido) 

            self.__relacionTransporteCiudad(id_transporte,next_ciudad)
        
#Borrar modelo
    def eliminaModelo(self):
        self.session.run("MATCH(n) detach DELETE n")


#Main
if __name__ == '__main__':

    modelo = Modelo("nico1011")
    modelo.eliminaModelo()
    modelo.crearModelo('Modelo.txt')
    
    
    modelo.calcularPrecioDistancia("Valencia","Zaragoza","tipo_03")

    #modelo.actualizacionEnvioTransporte("Vehiculo_1","Pedido_1")
    #modelo.actualizacionEnvioTransporte("Vehiculo_1","Pedido_1")
    #modelo.actualizacionEnvioTransporte("Vehiculo_1","Pedido_1")

    modelo.session.close()
    modelo.conexion.close() 

