DELIMITER $$

DROP PROCEDURE AjouterErreur;
CREATE PROCEDURE AjouterErreur(
    IN con INT,
    IN code_erreur INT
)
BEGIN
    INSERT INTO erreur_con (idcon, etat, code_err, date_err)
    VALUES (con, False, code_erreur, NOW());
END $$


CREATE PROCEDURE EffacerErreur(
    IN con INT,
    IN code_erreur VARCHAR(300)
)
BEGIN
    DELETE FROM erreur_con WHERE idcon=con AND code_err=code_erreur;
END $$


DROP PROCEDURE VerifierErreur;
CREATE PROCEDURE VerifierErreur(
    IN v_con_id INT 
)
BEGIN 
    DECLARE message_erreur BOOLEAN;
    DECLARE nb_err INT;
    SELECT 
        CASE
            WHEN (
                SELECT COUNT(*) FROM fonctionement 
                JOIN campagne ON fonctionement.idcampagne = campagne.id
                JOIN con ON con.idcampagne = campagne.id
                WHERE con.id = v_con_id
                ) = (
                SELECT COUNT(*) FROM message 
                JOIN con ON con.ID = message.idcon 
                JOIN fonctionement ON fonctionement.id = message.idfonc
                WHERE con.id= v_con_id
                ) THEN TRUE
            ELSE FALSE
        END
        INTO message_erreur; 
    IF message_erreur IS False THEN 
        SELECT COUNT(*) INTO nb_err FROM erreur_con WHERE idcon=v_con_id AND code_err=1 AND etat=False;
        IF nb_err = 0 THEN 
            CALL AjouterErreur(v_con_id, 1);
        END IF;
    END IF;
END$$ 



DELIMITER ;


